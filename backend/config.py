from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSettings:
    model_worker_url: str = os.getenv("MODEL_WORKER_URL", "http://127.0.0.1:8003").rstrip("/")
    request_timeout: float = float(os.getenv("BACKEND_REQUEST_TIMEOUT", "120"))
    model_catalog_url: str = os.getenv("MODEL_CATALOG_URL", "https://models.dev/api.json")
    model_catalog_proxy: str = os.getenv("MODEL_CATALOG_PROXY", "")


settings = BackendSettings()
