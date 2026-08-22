import base64
import tempfile
import unittest
from pathlib import Path

from chat_store import DEFAULT_AGENT_ID, create_app


class ChatStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "chat-data.sqlite3"
        self.app = create_app(self.database_path, testing=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_agent_and_session_message_lifecycle(self):
        agents = self.client.get("/api/chat/agents").get_json()
        self.assertEqual(agents[0]["id"], DEFAULT_AGENT_ID)

        session = self.client.post("/api/chat/sessions", json={"agent_id": DEFAULT_AGENT_ID}).get_json()
        self.assertEqual(session["agentId"], DEFAULT_AGENT_ID)

        message = self.client.post(
            f"/api/chat/sessions/{session['id']}/messages",
            json={"role": "user", "type": "text", "content": "Hello from a saved conversation"},
        ).get_json()
        self.assertEqual(message["content"], "Hello from a saved conversation")

        stored_session = self.client.get("/api/chat/sessions").get_json()[0]
        self.assertEqual(stored_session["title"], "Hello from a saved conversation")
        self.assertEqual(stored_session["preview"], "Hello from a saved conversation")

    def test_audio_and_agent_deletion_are_persisted(self):
        agent = self.client.post(
            "/api/chat/agents",
            json={
                "name": "Telephone Agent", "provider": "custom", "base_url": "http://127.0.0.1:11434/v1",
                "request_path": "/v1/chat/completions", "api_key": "local-test-key", "model": "qwen",
            },
        ).get_json()
        self.assertEqual(agent["requestPath"], "/v1/chat/completions")
        self.assertEqual(agent["apiKey"], "local-test-key")
        session = self.client.post("/api/chat/sessions", json={"agent_id": agent["id"]}).get_json()
        audio = base64.b64encode(b"opus bytes").decode()
        self.client.post(
            f"/api/chat/sessions/{session['id']}/messages",
            json={"role": "user", "type": "audio", "content": "Voice note", "mime_type": "audio/webm", "duration": 3, "audio_base64": audio},
        )

        messages = self.client.get(f"/api/chat/sessions/{session['id']}/messages").get_json()
        self.assertEqual(messages[0]["audioBase64"], audio)
        self.assertEqual(messages[0]["mimeType"], "audio/webm")

        self.client.delete(f"/api/chat/agents/{agent['id']}")
        updated_session = self.client.get("/api/chat/sessions").get_json()[0]
        self.assertEqual(updated_session["agentId"], DEFAULT_AGENT_ID)


if __name__ == "__main__":
    unittest.main()
