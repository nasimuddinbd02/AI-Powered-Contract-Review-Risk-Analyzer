"""Embedding client (SRS FR-1.3 / 2.3) — real OpenAI embeddings only.

Uses OpenAI ``text-embedding-3-small``. If no OpenAI key is configured, embedding
raises a clear error (no mock vectors) so the system never silently degrades.
"""
from __future__ import annotations

import math

from .config import get_settings
from .logging import get_logger, trace

log = get_logger("embeddings")

# text-embedding-3-small dimensionality.
EMBED_DIM = 1536


class EmbeddingsNotConfiguredError(RuntimeError):
    """Raised when embedding is attempted with no OpenAI key configured."""


class EmbeddingClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model = self.settings.embedding_model
        self._client = None
        if self.settings.has_openai:
            try:
                import openai  # type: ignore

                self._client = openai.OpenAI(api_key=self.settings.openai_api_key)
            except Exception as exc:  # pragma: no cover
                log.error("Failed to init OpenAI embeddings client: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts as unit-normalised vectors."""
        if not texts:
            return []
        if self._client is None:
            raise EmbeddingsNotConfiguredError(
                "OPENAI_API_KEY is required for embeddings. Add it to your .env and restart."
            )
        with trace("embeddings.embed", count=len(texts), model=self.model) as t:
            resp = self._client.embeddings.create(model=self.model, input=texts)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                t.tokens_in = getattr(usage, "prompt_tokens", 0)
            return [_normalize(d.embedding) for d in resp.data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else list(vec)


_client: EmbeddingClient | None = None


def get_embedder() -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient()
    return _client


def reset_embedder() -> None:
    """Clear the cached client (used by tests)."""
    global _client
    _client = None
