import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from qwen_asr.model_settings import ModelSettingsStore
from qwen_asr.voice_agent import LangChainVoiceAgent, TTSClient, _content_to_text


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


class VoiceAgentTests(unittest.TestCase):
    def test_tts_client_sends_json_and_returns_wav(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return FakeResponse(b"RIFF-test")

        client = TTSClient(timeout=9)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            audio = client.synthesize("你好", language="Chinese", speaker="Vivian")
        self.assertEqual(audio, b"RIFF-test")
        self.assertEqual(captured["payload"]["text"], "你好")
        self.assertEqual(captured["timeout"], 9)

    def test_unconfigured_agent_uses_explicit_echo_mode(self):
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict(os.environ, {}, clear=True):
                agent = LangChainVoiceAgent(
                    settings_store=ModelSettingsStore(config_dir)
                )
            self.assertEqual(agent.status()["mode"], "echo")
            self.assertIn("测试电话", agent.chat("测试电话", "call-1"))

    def test_multiblock_langchain_content_is_flattened(self):
        content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]
        self.assertEqual(_content_to_text(content), "Hello world")

    def test_browser_history_can_restore_model_context(self):
        agent = LangChainVoiceAgent()
        captured = {}

        def invoke(messages):
            captured["messages"] = messages
            return SimpleNamespace(content="restored")

        connection = {"configured": True, "model": "test"}
        model = SimpleNamespace(invoke=invoke)
        history = [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ]
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=model
        ):
            reply = agent.chat("Current question", "restored-session", history=history)

        self.assertEqual(reply, "restored")
        self.assertEqual(captured["messages"][1:3], history)


if __name__ == "__main__":
    unittest.main()
