from __future__ import annotations

from functools import lru_cache

from backend.config import settings
from backend.modules.model_worker import ModelWorkerAdapter


@lru_cache(maxsize=1)
def get_model_worker() -> ModelWorkerAdapter:
    return ModelWorkerAdapter(settings.model_worker_url, settings.request_timeout)
