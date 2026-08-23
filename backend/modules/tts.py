from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from backend.dependencies import get_model_worker
from backend.modules.model_worker import ModelWorkerAdapter


router = APIRouter(prefix="/api/tts", tags=["tts"])
Worker = Annotated[ModelWorkerAdapter, Depends(get_model_worker)]


@router.post("/stream")
async def stream(request: Request, worker: Worker) -> Response:
    return await worker.stream(request, "/api/tts/stream")


@router.api_route("", methods=["POST"])
async def synthesize(request: Request, worker: Worker) -> Response:
    return await worker.request(request, "/api/tts")
