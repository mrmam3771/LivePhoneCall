from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from backend.config import settings

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "models-dev.json"
CACHE_TTL_SECONDS = 24 * 60 * 60

_catalog: dict[str, Any] | None = None
_catalog_loaded_at = 0.0
_catalog_lock = asyncio.Lock()


def compact_catalog(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for provider_id, provider in payload.items():
        models = {}
        for model_id, model in provider.get("models", {}).items():
            models[model_id] = {
                key: model.get(key)
                for key in (
                    "id",
                    "name",
                    "description",
                    "family",
                    "release_date",
                    "last_updated",
                    "reasoning",
                    "tool_call",
                )
                if model.get(key) is not None
            }
        result[provider_id] = {
            "id": provider.get("id", provider_id),
            "name": provider.get("name", provider_id),
            "api": provider.get("api", ""),
            "models": models,
        }
    return result


def read_cache() -> tuple[dict[str, Any] | None, float]:
    try:
        modified_at = CACHE_PATH.stat().st_mtime
        return json.loads(CACHE_PATH.read_text(encoding="utf-8")), modified_at
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return None, 0.0


def write_cache(catalog: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = CACHE_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(catalog, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temporary_path.replace(CACHE_PATH)


async def load_catalog(force_refresh: bool = False) -> dict[str, Any]:
    global _catalog, _catalog_loaded_at

    now = time.time()
    if not force_refresh and _catalog and now - _catalog_loaded_at < CACHE_TTL_SECONDS:
        return _catalog

    async with _catalog_lock:
        now = time.time()
        if not force_refresh and _catalog and now - _catalog_loaded_at < CACHE_TTL_SECONDS:
            return _catalog

        cached, cached_at = read_cache()
        if not force_refresh and cached and now - cached_at < CACHE_TTL_SECONDS:
            _catalog, _catalog_loaded_at = cached, cached_at
            return cached

        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                proxy=settings.model_catalog_proxy or None,
            ) as client:
                response = await client.get(settings.model_catalog_url)
                response.raise_for_status()
            fresh = compact_catalog(response.json())
            write_cache(fresh)
            _catalog, _catalog_loaded_at = fresh, now
            return fresh
        except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError) as error:
            if cached:
                _catalog, _catalog_loaded_at = cached, cached_at
                return cached
            reason = str(error) or type(error).__name__
            raise HTTPException(status_code=503, detail=f"Model catalog is unavailable: {reason}") from error


@router.get("/models")
async def models(refresh: bool = Query(False)) -> dict[str, Any]:
    return await load_catalog(force_refresh=refresh)
