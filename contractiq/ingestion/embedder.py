"""Embedding + vector storage (SRS FR-1.3).

Embeds chunks (OpenAI or mock) and loads them into a per-contract vector store.
"""
from __future__ import annotations

from ..core.embeddings import EMBED_DIM, get_embedder
from ..core.logging import get_logger, trace
from ..core.models import Chunk
from ..core.vector_store import VectorStore

log = get_logger("ingestion.embedder")


def embed_chunks(chunks: list[Chunk]) -> VectorStore:
    """Embed ``chunks`` in place and return a populated :class:`VectorStore`."""
    embedder = get_embedder()
    store = VectorStore(dim=EMBED_DIM)
    if not chunks:
        return store
    with trace("ingestion.embed", count=len(chunks), model=embedder.model):
        vectors = embedder.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, vectors):
            chunk.embedding = vec
        store.add(chunks)
    log.info("Embedded %d chunks (%s) into %s store",
             len(chunks), embedder.model, store.backend)
    return store
