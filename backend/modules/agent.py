from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from backend.dependencies import get_model_worker
from backend.modules.model_worker import ModelWorkerAdapter


router = APIRouter(prefix="/api/agent", tags=["agent"])
Worker = Annotated[ModelWorkerAdapter, Depends(get_model_worker)]


@router.post("/stream")
async def stream(request: Request, worker: Worker) -> Response:
    return await worker.stream(request, "/api/agent/stream")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def agent(request: Request, path: str, worker: Worker) -> Response:
    return await worker.request(request, f"/api/agent/{path}")
