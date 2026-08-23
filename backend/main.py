from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.modules import agent, catalog, chat, tts, voice


@asynccontextmanager
async def lifespan(_app: FastAPI):
    chat.initialize()
    yield


app = FastAPI(title="Qwen Voice Backend", version="0.2.0", lifespan=lifespan)
app.include_router(voice.router)
app.include_router(agent.router)
app.include_router(tts.router)
app.include_router(chat.router)
app.include_router(catalog.router)


@app.get("/api/health", tags=["system"])
async def health():
    return {"ready": True, "service": "qwen-voice-backend"}


frontend_dist = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parent.parent / "frontend" / "dist"))
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
