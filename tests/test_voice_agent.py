import io
import json
import os
import sys
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
        self.assertEqual(captured["messages"][:2], history)

    def test_streaming_agent_yields_model_chunks(self):
        agent = LangChainVoiceAgent()
        model = SimpleNamespace(stream=lambda _messages: [SimpleNamespace(content="Hello"), SimpleNamespace(content=" world")])
        connection = {"configured": True, "model": "test"}
        with patch.object(agent, "_connection", return_value=connection), patch.object(agent, "_get_model", return_value=model):
            self.assertEqual(list(agent.stream_chat("Hi", "call-stream")), ["Hello", " world"])

    def test_streaming_agent_does_not_send_current_transcript_twice(self):
        agent = LangChainVoiceAgent()
        captured = {}

        def stream(messages):
            captured["messages"] = messages
            return [SimpleNamespace(content="I hear you")]

        model = SimpleNamespace(stream=stream)
        connection = {"configured": True, "model": "test"}
        history = [
            {"role": "assistant", "content": "Previous reply"},
            {"role": "user", "content": "Can you hear me?"},
        ]
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=model
        ):
            list(agent.stream_chat("Can you hear me?", "call-deduplicated", history=history))

        current_turns = [
            message for message in captured["messages"]
            if message["role"] == "user" and message["content"] == "Can you hear me?"
        ]
        self.assertEqual(len(current_turns), 1)

    def test_empty_agent_prompt_does_not_inject_a_system_message(self):
        agent = LangChainVoiceAgent()
        captured = {}

        def stream(messages):
            captured["messages"] = messages
            return [SimpleNamespace(content="Hello")]

        connection = {"configured": True, "model": "test"}
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=SimpleNamespace(stream=stream)
        ):
            list(agent.stream_chat(
                "Hi",
                "no-system-prompt",
                agent={"systemPrompt": "", "model": "test", "apiKey": "test-key"},
            ))

        self.assertEqual(captured["messages"], [{"role": "user", "content": "Hi"}])

    def test_explicit_agent_prompt_is_sent_as_a_system_message(self):
        agent = LangChainVoiceAgent()
        captured = {}

        def stream(messages):
            captured["messages"] = messages
            return [SimpleNamespace(content="Hello")]

        connection = {"configured": True, "model": "test"}
        custom_agent = {
            "systemPrompt": "Answer as a receptionist.",
            "model": "test",
            "apiKey": "test-key",
        }
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=SimpleNamespace(stream=stream)
        ):
            list(agent.stream_chat("Hi", "custom-system-prompt", agent=custom_agent))

        self.assertEqual(
            captured["messages"][:2],
            [
                {"role": "system", "content": "Answer as a receptionist."},
                {"role": "user", "content": "Hi"},
            ],
        )

    def test_nvidia_reasoning_content_is_streamed_separately(self):
        agent = LangChainVoiceAgent()
        chunks = [
            SimpleNamespace(
                content="",
                additional_kwargs={"reasoning_content": "Analyze the request."},
            ),
            SimpleNamespace(content="Final answer.", additional_kwargs={}),
        ]
        connection = {"configured": True, "model": "test"}
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=SimpleNamespace(stream=lambda _messages: chunks)
        ):
            events = list(agent.stream_chat("Hi", "nvidia-reasoning", with_kinds=True))

        self.assertEqual(
            events,
            [("thinking", "Analyze the request."), ("token", "Final answer.")],
        )

    def test_cumulative_nvidia_snapshots_are_converted_to_token_deltas(self):
        agent = LangChainVoiceAgent()
        chunks = [
            SimpleNamespace(content="作为", additional_kwargs={}),
            SimpleNamespace(content="作为AI", additional_kwargs={}),
            SimpleNamespace(content="作为AI助手", additional_kwargs={}),
            SimpleNamespace(content="，你好。", additional_kwargs={}),
        ]
        connection = {"configured": True, "model": "test"}
        with patch.object(agent, "_connection", return_value=connection), patch.object(
            agent, "_get_model", return_value=SimpleNamespace(stream=lambda _messages: chunks)
        ):
            events = list(agent.stream_chat("你好", "cumulative-nvidia", with_kinds=True))

        self.assertEqual(
            events,
            [("token", "作为"), ("token", "AI"), ("token", "助手"), ("token", "，你好。")],
        )
        self.assertEqual(
            list(agent.history["cumulative-nvidia"])[-1]["content"],
            "作为AI助手，你好。",
        )

    def test_nvidia_endpoint_uses_provider_specific_langchain_adapter(self):
        captured = {}

        def fake_chat_nvidia(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace()

        fake_module = SimpleNamespace(ChatNVIDIA=fake_chat_nvidia)
        connection = {
            "id": "nvidia",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "protocol": "openai",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key": "test-key",
            "temperature": 0.2,
            "max_tokens": 256,
        }
        with patch.dict(sys.modules, {"langchain_nvidia_ai_endpoints": fake_module}):
            LangChainVoiceAgent()._build_model(connection)

        self.assertEqual(captured["model"], connection["model"])
        self.assertEqual(captured["base_url"], connection["base_url"])
        self.assertEqual(captured["api_key"], "test-key")
        self.assertGreater(captured["max_completion_tokens"], captured["reasoning_budget"])
        self.assertTrue(captured["chat_template_kwargs"]["enable_thinking"])


if __name__ == "__main__":
    unittest.main()
