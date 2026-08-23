"""Persistent multi-provider model settings with separate credential storage."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Optional, Union


PROTOCOLS = {"openai", "anthropic", "google_genai"}
PROVIDER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
PRIVATE_PROVIDER_FIELDS = {"api_key", "configured", "has_api_key", "revision"}

DEFAULT_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "openai",
        "name": "OpenAI",
        "protocol": "openai",
        "base_url": "",
        "model": "gpt-5-mini",
        "models": ["gpt-5.5", "gpt-5-mini", "gpt-5-nano", "gpt-4.1-mini"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "protocol": "anthropic",
        "base_url": "",
        "model": "claude-sonnet-4-6",
        "models": ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "protocol": "google_genai",
        "base_url": "",
        "model": "gemini-3.1-flash-lite-preview",
        "models": ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "dashscope",
        "name": "Alibaba DashScope",
        "protocol": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "protocol": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "moonshot",
        "name": "Moonshot AI",
        "protocol": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-k2.5",
        "models": ["kimi-k2.5", "moonshot-v1-32k"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "protocol": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-5-mini",
        "models": ["openai/gpt-5-mini", "anthropic/claude-sonnet-4.6", "google/gemini-3.1-pro-preview"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "siliconflow",
        "name": "SiliconFlow",
        "protocol": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-V3.2",
        "models": ["deepseek-ai/DeepSeek-V3.2", "Qwen/Qwen3-235B-A22B"],
        "requires_key": True,
        "built_in": True,
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "protocol": "openai",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen3:8b",
        "models": ["qwen3:8b", "qwen3:14b", "gpt-oss:20b"],
        "requires_key": False,
        "built_in": True,
    },
]


class ModelSettingsError(ValueError):
    """Raised when a model provider setting is invalid."""


class ModelSettingsStore:
    def __init__(self, config_dir: Optional[Union[Path, str]] = None):
        configured_dir = os.getenv("VOICE_AGENT_CONFIG_DIR", "").strip()
        self.config_dir = Path(config_dir or configured_dir or ".voice-agent").resolve()
        self.models_path = self.config_dir / "models.json"
        self.auth_path = self.config_dir / "auth.json"
        self._lock = threading.RLock()
        self._providers = {item["id"]: copy.deepcopy(item) for item in DEFAULT_PROVIDERS}
        self._active_provider = "openai"
        self._keys: dict[str, str] = {}
        self._revision = 0
        self._load()

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelSettingsError(f"Cannot read {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ModelSettingsError(f"{path} must contain a JSON object")
        return loaded

    def _load(self) -> None:
        with self._lock:
            models = self._load_json(self.models_path)
            legacy_keys: dict[str, str] = {}
            for provider in models.get("providers", []):
                if isinstance(provider, dict) and provider.get("id"):
                    provider_id = str(provider["id"])
                    if provider.get("api_key"):
                        legacy_keys[provider_id] = str(provider["api_key"])
                    provider = {
                        key: value
                        for key, value in provider.items()
                        if key not in PRIVATE_PROVIDER_FIELDS
                    }
                    current = self._providers.get(provider_id, {})
                    self._providers[provider_id] = {**current, **provider}
            active = str(models.get("active_provider") or self._active_provider)
            if active in self._providers:
                self._active_provider = active

            auth = self._load_json(self.auth_path)
            keys = auth.get("keys", {})
            self._keys = legacy_keys
            if isinstance(keys, dict):
                self._keys.update({str(key): str(value) for key, value in keys.items() if value})
            if legacy_keys:
                self._persist()

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")
        temporary.replace(path)

    def _persist(self) -> None:
        self._write_json(
            self.models_path,
            {
                "active_provider": self._active_provider,
                "providers": list(self._providers.values()),
            },
        )
        self._write_json(self.auth_path, {"keys": self._keys})
        try:
            self.auth_path.chmod(0o600)
        except OSError:
            pass

    def public_settings(self) -> dict[str, Any]:
        with self._lock:
            providers = []
            for provider in self._providers.values():
                public = {
                    key: copy.deepcopy(value)
                    for key, value in provider.items()
                    if key not in PRIVATE_PROVIDER_FIELDS
                }
                public["has_api_key"] = bool(self._keys.get(provider["id"]))
                public["configured"] = bool(public.get("model")) and (
                    not public.get("requires_key", True) or public["has_api_key"]
                )
                providers.append(public)
            return {
                "active_provider": self._active_provider,
                "providers": providers,
                "revision": self._revision,
            }

    def connection(self, provider_id: Optional[str] = None) -> dict[str, Any]:
        with self._lock:
            selected = provider_id or self._active_provider
            if selected not in self._providers:
                raise ModelSettingsError("unknown provider")
            provider = copy.deepcopy(self._providers[selected])
            provider["api_key"] = self._keys.get(selected, "")
            provider["configured"] = bool(provider.get("model")) and (
                not provider.get("requires_key", True) or bool(provider["api_key"])
            )
            provider["revision"] = self._revision
            return provider

    def active_connection(self) -> dict[str, Any]:
        return self.connection()

    def _validated_provider(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        provider_id = str(payload.get("id") or "").strip().lower()
        if not PROVIDER_ID_PATTERN.fullmatch(provider_id):
            raise ModelSettingsError("provider id must use lowercase letters, numbers, '-' or '_'")
        current = self._providers.get(provider_id, {})
        protocol = str(payload.get("protocol", current.get("protocol", "openai"))).strip()
        if protocol not in PROTOCOLS:
            raise ModelSettingsError("unsupported provider protocol")
        models = payload.get("models", current.get("models", []))
        if not isinstance(models, list):
            raise ModelSettingsError("models must be a list")

        provider = {
            **current,
            "id": provider_id,
            "name": str(payload.get("name", current.get("name", provider_id))).strip() or provider_id,
            "protocol": protocol,
            "base_url": str(payload.get("base_url", current.get("base_url", ""))).strip(),
            "model": str(payload.get("model", current.get("model", ""))).strip(),
            "models": list(models),
            "requires_key": bool(payload.get("requires_key", current.get("requires_key", True))),
            "built_in": bool(current.get("built_in", False)),
            "temperature": float(payload.get("temperature", current.get("temperature", 0.2))),
            "max_tokens": int(payload.get("max_tokens", current.get("max_tokens", 256))),
        }
        if not provider["model"]:
            raise ModelSettingsError("model is required")
        if not 0 <= provider["temperature"] <= 2:
            raise ModelSettingsError("temperature must be between 0 and 2")
        if not 1 <= provider["max_tokens"] <= 65536:
            raise ModelSettingsError("max_tokens must be between 1 and 65536")
        if protocol == "openai" and provider_id != "openai" and not provider["base_url"]:
            raise ModelSettingsError("base_url is required for OpenAI-compatible providers")

        api_key = self._keys.get(provider_id, "")
        supplied_key = payload.get("api_key")
        if isinstance(supplied_key, str) and supplied_key.strip():
            api_key = supplied_key.strip()
        if payload.get("clear_api_key"):
            api_key = ""
        return provider, api_key

    def preview_connection(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            provider, api_key = self._validated_provider(payload)
            provider["api_key"] = api_key
            provider["configured"] = bool(provider.get("model")) and (
                not provider.get("requires_key", True) or bool(api_key)
            )
            provider["revision"] = self._revision
            return provider

    def save_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            provider, api_key = self._validated_provider(payload)
            provider_id = provider["id"]
            configured = bool(provider.get("model")) and (
                not provider.get("requires_key", True) or bool(api_key)
            )
            if payload.get("active") and not configured:
                raise ModelSettingsError("cannot activate a provider without its required API key")
            if provider_id == self._active_provider and provider_id in self._providers:
                was_configured = bool(self.connection(provider_id).get("configured"))
                if was_configured and not configured:
                    raise ModelSettingsError("activate another provider before removing the active API key")
            self._providers[provider_id] = provider
            if api_key:
                self._keys[provider_id] = api_key
            else:
                self._keys.pop(provider_id, None)
            if payload.get("active") or self._active_provider not in self._providers:
                self._active_provider = provider_id
            self._revision += 1
            self._persist()
            return self.public_settings()

    def set_active(self, provider_id: str) -> dict[str, Any]:
        with self._lock:
            connection = self.connection(provider_id)
            if not connection.get("configured"):
                raise ModelSettingsError("cannot activate a provider without its required API key")
            self._active_provider = provider_id
            self._revision += 1
            self._persist()
            return self.public_settings()

    def delete_provider(self, provider_id: str) -> dict[str, Any]:
        with self._lock:
            provider = self._providers.get(provider_id)
            if not provider:
                raise ModelSettingsError("unknown provider")
            if provider.get("built_in"):
                raise ModelSettingsError("built-in providers cannot be deleted")
            if self._active_provider == provider_id:
                raise ModelSettingsError("activate another provider before deleting the current provider")
            del self._providers[provider_id]
            self._keys.pop(provider_id, None)
            self._revision += 1
            self._persist()
            return self.public_settings()
