from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response, StreamingResponse


class ModelWorkerAdapter:
    """Hide the isolated ASR/TTS runtime behind one small async interface."""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def request(self, request: Request, path: str) -> Response:
        body = await request.body()
        params = list(request.query_params.multi_items())
        headers = {key: value for key, value in request.headers.items() if key.lower() in {"content-type", "accept"}}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                upstream = await client.request(request.method, f"{self.base_url}{path}", params=params, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Model worker unavailable: {exc}") from exc
        response_headers = {key: value for key, value in upstream.headers.items() if key.lower() in {"content-type", "cache-control", "x-audio-format", "x-sample-rate"}}
        return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)

    async def stream(self, request: Request, path: str) -> StreamingResponse:
        body = await request.body()
        params = list(request.query_params.multi_items())
        headers = {key: value for key, value in request.headers.items() if key.lower() in {"content-type", "accept"}}
        client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None))
        try:
            upstream_request = client.build_request(request.method, f"{self.base_url}{path}", params=params, content=body, headers=headers)
            upstream = await client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            await client.aclose()
            raise HTTPException(status_code=503, detail=f"Model worker unavailable: {exc}") from exc

        async def content() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_raw():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        response_headers = {key: value for key, value in upstream.headers.items() if key.lower() in {"cache-control", "x-audio-format", "x-sample-rate"}}
        return StreamingResponse(content(), status_code=upstream.status_code, media_type=upstream.headers.get("content-type"), headers=response_headers)
