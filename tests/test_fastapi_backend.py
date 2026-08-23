import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.modules.chat as chat_module
from backend.modules.catalog import compact_catalog
from backend.main import app


class FastAPIBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "chat.sqlite3"
        self.path_patch = patch.object(chat_module, "DEFAULT_DATABASE_PATH", self.database_path)
        self.path_patch.start()
        chat_module.initialize()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_system_and_chat_modules_are_served_by_fastapi(self):
        self.assertEqual(self.client.get("/api/health").json()["service"], "qwen-voice-backend")
        bootstrap = self.client.get("/api/chat/bootstrap")
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(bootstrap.json()["providers"][0]["id"], "deepseek")

    def test_chat_session_and_message_lifecycle(self):
        session = self.client.post("/api/chat/sessions", json={}).json()
        message = self.client.post(
            f"/api/chat/sessions/{session['id']}/messages",
            json={"role": "user", "type": "text", "content": "FastAPI message"},
        )
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.json()["content"], "FastAPI message")
        stored_session = self.client.get("/api/chat/sessions").json()[0]
        self.assertEqual(stored_session["title"], "FastAPI message")

    def test_agent_can_be_created_without_system_instructions(self):
        response = self.client.post(
            "/api/chat/agents",
            json={"name": "No-prompt Agent", "systemPrompt": ""},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["systemPrompt"], "")

    def test_models_dev_catalog_preserves_provider_model_names_and_count(self):
        catalog = compact_catalog({
            "deepseek": {
                "id": "deepseek",
                "name": "DeepSeek",
                "api": "https://api.deepseek.com",
                "models": {
                    "deepseek-chat": {"id": "deepseek-chat", "name": "DeepSeek Chat"},
                    "deepseek-reasoner": {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner"},
                },
            },
        })

        self.assertEqual(catalog["deepseek"]["name"], "DeepSeek")
        self.assertEqual(len(catalog["deepseek"]["models"]), 2)
        self.assertEqual(catalog["deepseek"]["models"]["deepseek-reasoner"]["name"], "DeepSeek Reasoner")

    def test_session_insert_is_safe_when_model_id_was_added_by_migration(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DROP TABLE sessions")
            connection.execute("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id),
                    title TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    model_id TEXT NOT NULL DEFAULT 'deepseek-chat'
                )
            """)

        session = self.client.post("/api/chat/sessions", json={}).json()

        self.assertEqual(session["title"], "New conversation / 新会话")
        self.assertEqual(session["modelId"], "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
