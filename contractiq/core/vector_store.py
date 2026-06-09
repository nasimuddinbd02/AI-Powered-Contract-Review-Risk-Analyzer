"""Vector store abstraction (SRS 2.3 / 4.2).

Prefers FAISS when installed (``VECTOR_STORE=faiss``); otherwise transparently
falls back to a pure-NumPy / pure-Python in-memory cosine index so retrieval
works everywhere. Stores are per-contract and held in memory only, satisfying
the ephemeral-storage security requirement (SRS 4.4).
"""
from __future__ import annotations

from .config import get_settings
from .logging import get_logger
from .models import Chunk, ChunkRef

log = get_logger("vector_store")

try:
    import numpy as np

    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _HAS_NUMPY = False

try:
    import faiss  # type: ignore

    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False


class VectorStore:
    """A per-contract similarity index over embedded chunks.

    Embeddings are unit-normalised upstream, so inner product == cosine
    similarity. Returns scores in ``[-1, 1]`` (typically ``[0, 1]``).
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.chunks: list[Chunk] = []
        settings = get_settings()
        self.backend = "faiss" if (_HAS_FAISS and settings.vector_store == "faiss") else "memory"
        self._faiss_index = None
        self._matrix = None  # numpy array fallback
        if self.backend == "faiss":
            self._faiss_index = faiss.IndexFlatIP(dim)

    def add(self, chunks: list[Chunk]) -> None:
        vectors = [c.embedding for c in chunks if c.embedding is not None]
        if not vectors:
            return
        self.chunks.extend(chunks)
        if self.backend == "faiss":
            self._faiss_index.add(np.array(vectors, dtype="float32"))  # type: ignore[union-attr]
        elif _HAS_NUMPY:
            arr = np.array(vectors, dtype="float32")
            self._matrix = arr if self._matrix is None else np.vstack([self._matrix, arr])

    def search(self, query_vec: list[float], top_k: int = 5) -> list[ChunkRef]:
        """Return the ``top_k`` most similar chunks as ``ChunkRef`` objects."""
        if not self.chunks:
            return []
        top_k = min(top_k, len(self.chunks))

        if self.backend == "faiss":
            scores, idxs = self._faiss_index.search(  # type: ignore[union-attr]
                np.array([query_vec], dtype="float32"), top_k
            )
            pairs = list(zip(idxs[0].tolist(), scores[0].tolist()))
        elif _HAS_NUMPY and self._matrix is not None:
            sims = self._matrix @ np.array(query_vec, dtype="float32")
            order = np.argsort(-sims)[:top_k]
            pairs = [(int(i), float(sims[i])) for i in order]
        else:  # pure-python fallback
            sims = [
                (i, _dot(query_vec, c.embedding))
                for i, c in enumerate(self.chunks)
                if c.embedding is not None
            ]
            sims.sort(key=lambda p: p[1], reverse=True)
            pairs = sims[:top_k]

        refs: list[ChunkRef] = []
        for idx, score in pairs:
            if idx < 0:
                continue
            c = self.chunks[idx]
            refs.append(ChunkRef(chunk_id=c.chunk_id, page_num=c.page_num, text=c.text, score=round(score, 4)))
        return refs


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
