"""RAG retriever (SRS FR-6).

Embeds a query, retrieves the top-5 chunks by cosine similarity, and filters out
results below the configured similarity threshold (default 0.75).
"""
from __future__ import annotations

from ..core.config import get_settings
from ..core.embeddings import get_embedder
from ..core.logging import get_logger, trace
from ..core.models import ChunkRef
from ..core.vector_store import VectorStore

log = get_logger("rag.retriever")


class Retriever:
    def __init__(self, store: VectorStore, threshold: float | None = None) -> None:
        self.store = store
        self.embedder = get_embedder()
        self.threshold = threshold if threshold is not None else get_settings().similarity_threshold

    def retrieve(self, query: str, top_k: int = 5, apply_threshold: bool = True) -> list[ChunkRef]:
        """Return up to ``top_k`` chunks above the similarity threshold."""
        with trace("rag.retrieve", top_k=top_k, threshold=self.threshold):
            query_vec = self.embedder.embed_one(query)
            refs = self.store.search(query_vec, top_k=top_k)
            if apply_threshold:
                refs = [r for r in refs if r.score >= self.threshold]
            log.info("Retrieved %d chunks for query (threshold=%.2f)", len(refs), self.threshold)
            return refs
