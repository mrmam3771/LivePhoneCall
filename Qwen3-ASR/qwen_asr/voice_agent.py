"""LangChain conversation adapter and client for the isolated TTS service."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections import defaultdict, deque
from typing import Any, Optional

from qwen_asr.model_settings import ModelSettingsStore


class VoiceServiceError(RuntimeError):
    """Raised when the internal Qwen3-TTS service cannot fulfill a request."""


class TTSClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.base_url}/health", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=3.0) as response:
                return json.loads(response.read())
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {"ready": False, "error": str(exc)}

    def synthesize(
        self,
        text: str,
        language: str = "Auto",
        speaker: str = "Vivian",
    ) -> bytes:
        payload = json.dumps(
            {"text": text, "language": language, "speaker": speaker}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/synthesize",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise VoiceServiceError(f"TTS request failed ({exc.code}): {detail}") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise VoiceServiceError(f"TTS service unavailable: {exc}") from exc

    def synthesize_stream(self, text: str, language: str = "Auto", speaker: str = "Vivian"):
        payload = json.dumps({"text": text, "language": language, "speaker": speaker}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/synthesize-stream", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                sample_rate = response.headers.get("X-Sample-Rate", "24000")
                for chunk in iter(lambda: response.read(8192), b""):
                    yield chunk, sample_rate
        except urllib.error.HTTPError as exc:
            raise VoiceServiceError(f"Streaming TTS request failed ({exc.code}): {exc.read().decode('utf-8', errors='replace')}") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise VoiceServiceError(f"TTS service unavailable: {exc}") from exc


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(content)


def _stream_delta(accumulated: str, incoming: str) -> tuple[str, str]:
    """Accept both token deltas and provider-specific cumulative snapshots."""
    if not incoming:
        return "", accumulated
    if accumulated and incoming.startswith(accumulated):
        return incoming[len(accumulated):], incoming
    return incoming, accumulated + incoming


def _history_without_current_user(
    history: Optional[list[dict[str, str]]], text: str
) -> list[dict[str, str]]:
    messages = list(history or [])
    if messages and messages[-1].get("role") == "user":
        previous = str(messages[-1].get("content", "")).strip()
        if previous == text.strip():
            messages.pop()
    return messages


class LangChainVoiceAgent:
    """Small stateful LangChain adapter suitable for turn-based call testing."""

    def __init__(
        self,
        history_turns: int = 8,
        settings_store: Optional[ModelSettingsStore] = None,
    ):
        self.model_name = os.getenv("VOICE_AGENT_MODEL", "").strip()
        self.settings_store = settings_store or ModelSettingsStore()
        self.system_prompt = os.getenv("VOICE_AGENT_SYSTEM_PROMPT", "").strip()
        self.history: defaultdict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=history_turns * 2)
        )
        self._model: Any = None
        self._model_signature = ""
        self._lock = threading.Lock()
        self._chat_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self._connection().get("configured"))

    def _connection(self, provider_id: Optional[str] = None) -> dict[str, Any]:
        if provider_id or self.settings_store.models_path.exists() or not self.model_name:
            return self.settings_store.connection(provider_id)
        return {
            "id": "environment",
            "name": "Environment",
            "model": self.model_name,
            "protocol": "",
            "base_url": os.getenv("VOICE_AGENT_BASE_URL", "").strip(),
            "api_key": os.getenv("VOICE_AGENT_API_KEY", "").strip(),
            "temperature": float(os.getenv("VOICE_AGENT_TEMPERATURE", "0.2")),
            "max_tokens": int(os.getenv("VOICE_AGENT_MAX_TOKENS", "256")),
            "configured": True,
            "revision": 0,
        }

    def status(self) -> dict[str, Any]:
        connection = self._connection()
        configured = bool(connection.get("configured"))
        return {
            "configured": configured,
            "mode": "langchain" if configured else "echo",
            "provider": connection.get("id"),
            "provider_name": connection.get("name"),
            "model": connection.get("model") or None,
        }

    def _build_model(self, connection: dict[str, Any]) -> Any:
        base_url = str(connection.get("base_url") or "")
        if "integrate.api.nvidia.com" in base_url.lower():
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            max_tokens = max(int(connection.get("max_tokens", 256)), 1024)
            reasoning_budget = min(512, max_tokens - 1)
            return ChatNVIDIA(
                model=str(connection["model"]),
                base_url=base_url,
                api_key=str(connection.get("api_key") or ""),
                temperature=float(connection.get("temperature", 0.2)),
                max_completion_tokens=max_tokens,
                chat_template_kwargs={"enable_thinking": True},
                reasoning_budget=reasoning_budget,
                timeout=float(os.getenv("VOICE_AGENT_TIMEOUT", "45")),
            )

        from langchain.chat_models import init_chat_model

        kwargs: dict[str, Any] = {
            "temperature": float(connection.get("temperature", 0.2)),
            "timeout": float(os.getenv("VOICE_AGENT_TIMEOUT", "45")),
            "max_tokens": int(connection.get("max_tokens", 256)),
        }
        if protocol := connection.get("protocol"):
            kwargs["model_provider"] = protocol
        if api_key := connection.get("api_key"):
            kwargs["api_key"] = api_key
        if base_url := connection.get("base_url"):
            kwargs["base_url"] = base_url
        return init_chat_model(str(connection["model"]), **kwargs)

    def _get_model(self, connection: dict[str, Any]) -> Any:
        signature = json.dumps(connection, sort_keys=True, default=str)
        if self._model is not None and signature == self._model_signature:
            return self._model
        with self._lock:
            if self._model is None or signature != self._model_signature:
                self._model = self._build_model(connection)
                self._model_signature = signature
        return self._model

    def test_connection(self, payload: dict[str, Any]) -> str:
        connection = self.settings_store.preview_connection(payload)
        if not connection.get("configured"):
            raise ValueError("provider requires a model and API key")
        response = self._build_model(connection).invoke("Reply with OK only.")
        return _content_to_text(response.content).strip()

    def chat(
        self,
        text: str,
        conversation_id: str,
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        text = text.strip()
        if not text:
            raise ValueError("text is required")
        connection = self._connection()
        if not connection.get("configured"):
            return f"大模型尚未配置。语音链路已经收到：{text}"

        with self._chat_lock:
            messages: list[dict[str, str]] = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.extend(_history_without_current_user(history, text) if history is not None else self.history[conversation_id])
            messages.append({"role": "user", "content": text})
            response = self._get_model(connection).invoke(messages)
            reply = _content_to_text(response.content).strip()
            if not reply:
                raise RuntimeError("The language model returned an empty response")
            self.history[conversation_id].append({"role": "user", "content": text})
            self.history[conversation_id].append({"role": "assistant", "content": reply})
        return reply

    def stream_chat(
        self,
        text: str,
        conversation_id: str,
        history: Optional[list[dict[str, str]]] = None,
        agent: Optional[dict[str, Any]] = None,
        with_kinds: bool = False,
    ):
        """Yield reply text chunks for one call turn.

        A browser Agent may override the provider connection for this turn. The
        caller owns the credential and this process is intentionally localhost-only.
        """
        text = text.strip()
        if not text:
            raise ValueError("text is required")
        connection = self._connection()
        prompt = self.system_prompt
        if agent:
            prompt = str(agent.get("systemPrompt", "")).strip()
            provider = str(agent.get("provider") or "openai")
            protocol = {"anthropic": "anthropic", "google": "google_genai", "google_genai": "google_genai"}.get(provider, "openai")
            base_url = str(agent.get("baseUrl") or "")
            local_endpoint = base_url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0"))
            connection = {
                "id": provider,
                "model": str(agent.get("model") or ""),
                "protocol": protocol,
                "base_url": base_url,
                "api_key": str(agent.get("apiKey") or ""),
                "temperature": 0.2,
                "max_tokens": 256,
                "configured": bool(agent.get("model")) and bool(agent.get("apiKey") or local_endpoint),
            }
        if not connection.get("configured"):
            yield f"大模型尚未配置。语音链路已经收到：{text}"
            return

        messages: list[dict[str, str]] = []
        if prompt:
            messages.append({"role": "system", "content": prompt})
        messages.extend(_history_without_current_user(history, text) if history is not None else self.history[conversation_id])
        messages.append({"role": "user", "content": text})
        parts: list[str] = []
        text_accumulated = ""
        reasoning_accumulated = ""
        for chunk in self._get_model(connection).stream(messages):
            content = chunk.content
            emitted_text = False
            if with_kinds:
                additional = getattr(chunk, "additional_kwargs", {}) or {}
                reasoning = additional.get("reasoning_content") or additional.get("reasoning")
                if reasoning:
                    delta, reasoning_accumulated = _stream_delta(
                        reasoning_accumulated, str(reasoning)
                    )
                    if delta:
                        yield ("thinking", delta)
            if with_kinds and isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = str(block.get("type", ""))
                    piece = str(block.get("text") or block.get("reasoning") or "")
                    if not piece:
                        continue
                    if block_type in {"reasoning", "thinking"}:
                        delta, reasoning_accumulated = _stream_delta(
                            reasoning_accumulated, piece
                        )
                        if delta:
                            yield ("thinking", delta)
                    elif block_type == "text":
                        emitted_text = True
                        delta, text_accumulated = _stream_delta(text_accumulated, piece)
                        if delta:
                            parts.append(delta)
                            yield ("token", delta)
            if not with_kinds or not emitted_text:
                piece = _content_to_text(content)
                if piece:
                    delta, text_accumulated = _stream_delta(text_accumulated, piece)
                    if delta:
                        parts.append(delta)
                        yield ("token", delta) if with_kinds else delta
        reply = "".join(parts).strip()
        if not reply:
            raise RuntimeError("The language model returned an empty response")
        self.history[conversation_id].append({"role": "user", "content": text})
        self.history[conversation_id].append({"role": "assistant", "content": reply})
