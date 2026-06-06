from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import research
from app.api.websocket import router as ws_router
from app.core.config import get_settings
from app.core.llm import get_llm
from app.db.database import init_db
from app.services.embeddings import EmbeddingClient

app = FastAPI(title="SynthesisOS API", version="0.1.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_origin_regex=settings.origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(ws_router)


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    llm = get_llm()
    emb = EmbeddingClient()
    s = get_settings()
    print(
        f"[SynthesisOS] gemini={'on' if llm.enabled else 'off (demo mode)'} "
        f"pipeline_llm={'on' if llm.pipeline_llm_allowed else 'off'} "
        f"embeddings={emb.mode} max_rpm={s.gemini_max_rpm}"
    )


@app.get("/")
async def root():
    return {"service": "SynthesisOS", "docs": "/docs"}
