"""FastAPI application entry point (SRS 2.3).

Wires CORS, the MCP tool router, and the upload/analyze/chat/export routes into
a single stateless app. Run with::

    uvicorn contractiq.api.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..core.llm import get_llm
from ..core.embeddings import get_embedder
from ..core.logging import TRACES, get_logger
from ..auth.routes import auth_router, users_router
from ..mcp_server.server import router as mcp_router
from .routes import analyze, chat, export, upload

log = get_logger("api.main")

app = FastAPI(
    title="ContractIQ API",
    description="AI-Powered Contract Review & Risk Analyzer (see ContractIQ_SRS.docx)",
    version="1.0.0",
)

# CORS — frontend dev server (Next.js) on :3000 by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(mcp_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe + active model/provider banner."""
    settings = get_settings()
    llm = get_llm()
    embedder = get_embedder()
    return {
        "status": "ok",
        "llm_provider": llm.provider,
        "llm_model": llm.model or None,
        "llm_ready": llm.available,
        "embedding_model": settings.embedding_model,
        "embeddings_ready": embedder.available,
        "vector_store": settings.vector_store,
        "similarity_threshold": settings.similarity_threshold,
    }


@app.get("/traces", tags=["meta"])
def traces(limit: int = 50) -> dict:
    """Recent run traces — latency + token usage per step (SRS 4.6)."""
    recent = TRACES[-limit:]
    return {
        "count": len(recent),
        "total_recorded": len(TRACES),
        "traces": [
            {
                "name": t.name,
                "latency_ms": t.latency_ms,
                "tokens_in": t.tokens_in,
                "tokens_out": t.tokens_out,
                "metadata": t.metadata,
            }
            for t in recent
        ],
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "ContractIQ API", "docs": "/docs", "health": "/health"}
