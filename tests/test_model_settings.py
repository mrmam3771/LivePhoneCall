import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from qwen_asr.model_settings import ModelSettingsError, ModelSettingsStore
from qwen_asr.voice_agent import LangChainVoiceAgent


class ModelSettingsStoreTests(unittest.TestCase):
    def make_store(self, directory: str) -> ModelSettingsStore:
        return ModelSettingsStore(Path(directory))

    def test_default_catalog_contains_native_and_compatible_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            public = self.make_store(directory).public_settings()

        provider_ids = {provider["id"] for provider in public["providers"]}
        self.assertTrue({"openai", "anthropic", "google", "dashscope", "ollama"} <= provider_ids)
        self.assertNotIn("api_key", public["providers"][0])

    def test_api_key_is_stored_separately_and_never_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            store.save_provider(
                {
                    "id": "deepseek",
                    "name": "DeepSeek",
                    "protocol": "openai",
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "api_key": "secret-key",
                    "active": True,
                }
            )

            public = store.public_settings()
            provider = next(item for item in public["providers"] if item["id"] == "deepseek")
            active = store.active_connection()

            self.assertTrue(provider["has_api_key"])
            self.assertNotIn("secret-key", str(public))
            self.assertEqual(active["api_key"], "secret-key")
            self.assertNotIn("secret-key", (Path(directory) / "models.json").read_text("utf-8"))
            self.assertIn("secret-key", (Path(directory) / "auth.json").read_text("utf-8"))

    def test_blank_api_key_preserves_saved_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            store.save_provider({"id": "openai", "model": "gpt-5-mini", "api_key": "saved"})
            store.save_provider({"id": "openai", "model": "gpt-5.5", "api_key": ""})

            self.assertEqual(store.active_connection()["api_key"], "saved")

    def test_provider_cannot_be_activated_without_required_key(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)

            with self.assertRaises(ModelSettingsError):
                store.save_provider({"id": "openai", "model": "gpt-5-mini", "active": True})

            self.assertFalse((Path(directory) / "models.json").exists())

    def test_connection_preview_does_not_persist_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            preview = store.preview_connection(
                {
                    "id": "preview-local",
                    "name": "Preview Local",
                    "protocol": "openai",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "model": "draft-model",
                    "requires_key": False,
                }
            )

            self.assertTrue(preview["configured"])
            self.assertFalse((Path(directory) / "models.json").exists())
            self.assertNotIn("preview-local", {item["id"] for item in store.public_settings()["providers"]})

    def test_legacy_inline_api_key_is_migrated_but_never_public(self):
        with tempfile.TemporaryDirectory() as directory:
            config_dir = Path(directory)
            (config_dir / "models.json").write_text(
                '{"active_provider":"openai","providers":[{"id":"openai","api_key":"legacy"}]}',
                "utf-8",
            )
            store = self.make_store(directory)

            self.assertNotIn("legacy", str(store.public_settings()))
            self.assertEqual(store.active_connection()["api_key"], "legacy")
            self.assertNotIn("legacy", (config_dir / "models.json").read_text("utf-8"))
            self.assertIn("legacy", (config_dir / "auth.json").read_text("utf-8"))

    def test_active_key_cannot_be_cleared_until_another_provider_is_active(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            store.save_provider(
                {"id": "openai", "model": "gpt-5-mini", "api_key": "saved", "active": True}
            )

            with self.assertRaises(ModelSettingsError):
                store.save_provider({"id": "openai", "clear_api_key": True})

            self.assertEqual(store.active_connection()["api_key"], "saved")

    def test_active_custom_provider_must_be_switched_before_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            store.save_provider(
                {
                    "id": "local-active",
                    "name": "Local Active",
                    "protocol": "openai",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "model": "local-model",
                    "requires_key": False,
                    "active": True,
                }
            )

            with self.assertRaises(ModelSettingsError):
                store.delete_provider("local-active")

    def test_agent_rebuilds_model_when_active_provider_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            store.save_provider(
                {
                    "id": "local-one",
                    "name": "Local One",
                    "protocol": "openai",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "model": "qwen-local",
                    "requires_key": False,
                    "active": True,
                }
            )
            agent = LangChainVoiceAgent(settings_store=store)
            first_model = SimpleNamespace(invoke=lambda _messages: SimpleNamespace(content="first"))
            second_model = SimpleNamespace(invoke=lambda _messages: SimpleNamespace(content="second"))

            with patch(
                "langchain.chat_models.init_chat_model",
                side_effect=[first_model, second_model],
            ) as init:
                self.assertEqual(agent.chat("hello", "call-1"), "first")
                store.save_provider(
                    {
                        "id": "local-two",
                        "name": "Local Two",
                        "protocol": "openai",
                        "base_url": "http://127.0.0.1:1234/v1",
                        "model": "second-local",
                        "requires_key": False,
                        "active": True,
                    }
                )
                self.assertEqual(agent.chat("hello again", "call-1"), "second")

            self.assertEqual(init.call_count, 2)
            kwargs = init.call_args_list[0].kwargs
            self.assertEqual(init.call_args_list[0].args[0], "qwen-local")
            self.assertEqual(kwargs["model_provider"], "openai")
            self.assertEqual(kwargs["base_url"], "http://127.0.0.1:11434/v1")
            self.assertNotIn("api_key", kwargs)
            self.assertEqual(init.call_args_list[1].args[0], "second-local")


if __name__ == "__main__":
    unittest.main()
