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
        bootstrap = self.client.get("/api/chat/bootstrap").get_json()
        self.assertEqual(bootstrap["providers"][0]["id"], "deepseek")
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

    def test_audio_is_rejected_and_agent_deletion_reassigns_sessions(self):
        agent = self.client.post(
            "/api/chat/agents",
            json={"name": "Telephone Agent", "systemPrompt": "Be concise."},
        ).get_json()
        provider = self.client.post("/api/chat/providers", json={"name": "Local Ollama", "api": "openai-completions", "baseUrl": "http://127.0.0.1:11434/v1", "apiKey": "local-test-key"}).get_json()
        model = self.client.post("/api/chat/models", json={"name": "Local Qwen", "providerId": provider["id"], "request_path": "/v1/chat/completions", "model": "qwen"}).get_json()
        self.assertEqual(model["requestPath"], "/v1/chat/completions")
        self.assertEqual(model["providerId"], provider["id"])
        session = self.client.post("/api/chat/sessions", json={"agent_id": agent["id"], "model_id": model["id"]}).get_json()
        response = self.client.post(
            f"/api/chat/sessions/{session['id']}/messages",
            json={"role": "user", "type": "audio", "content": "Voice note"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not stored", response.get_json()["error"])

        self.client.delete(f"/api/chat/agents/{agent['id']}")
        updated_session = self.client.get("/api/chat/sessions").get_json()[0]
        self.assertEqual(updated_session["agentId"], DEFAULT_AGENT_ID)

        self.assertEqual(self.client.delete(f"/api/chat/providers/{provider['id']}").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/chat/models/{model['id']}").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/chat/providers/{provider['id']}").status_code, 204)


if __name__ == "__main__":
    unittest.main()
