from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from backend.dependencies import get_model_worker
from backend.modules.model_worker import ModelWorkerAdapter


router = APIRouter(tags=["voice"])
Worker = Annotated[ModelWorkerAdapter, Depends(get_model_worker)]


@router.api_route("/api/voice/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def voice(request: Request, path: str, worker: Worker) -> Response:
    return await worker.request(request, f"/api/voice/{path}")


@router.api_route("/api/start", methods=["POST"])
async def start(request: Request, worker: Worker) -> Response:
    return await worker.request(request, "/api/start")


@router.api_route("/api/chunk", methods=["POST"])
async def chunk(request: Request, worker: Worker) -> Response:
    return await worker.request(request, "/api/chunk")


@router.api_route("/api/finish", methods=["POST"])
async def finish(request: Request, worker: Worker) -> Response:
    return await worker.request(request, "/api/finish")
