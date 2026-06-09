"""Chunking (SRS FR-1.3).

Splits page text into ~512-token chunks with 64-token overlap. Uses LangChain's
``RecursiveCharacterTextSplitter`` when available; otherwise a built-in splitter
with equivalent behaviour keeps the pipeline dependency-light. Token counts are
approximated as ~4 characters/token (standard heuristic) when no tokenizer is
present.
"""
from __future__ import annotations

from ..core.logging import get_logger
from ..core.models import Chunk
from .parser import PageText

log = get_logger("ingestion.chunker")

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64
CHARS_PER_TOKEN = 4  # heuristic
CHUNK_CHARS = CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN


def chunk_pages(contract_id: str, pages: list[PageText]) -> list[Chunk]:
    """Convert extracted pages into overlapping :class:`Chunk` objects."""
    chunks: list[Chunk] = []
    splitter = _get_splitter()
    for page in pages:
        if not page.text.strip():
            continue
        if splitter is not None:
            pieces = splitter.split_text(page.text)
        else:
            pieces = _split_text(page.text)
        for piece in pieces:
            if piece.strip():
                chunks.append(
                    Chunk(
                        contract_id=contract_id,
                        page_num=page.page_num,
                        text=piece.strip(),
                        section_header=page.section_header,
                    )
                )
    log.info("Chunked %d pages into %d chunks", len(pages), len(chunks))
    return chunks


def _get_splitter():
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_CHARS,
            chunk_overlap=OVERLAP_CHARS,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    except Exception:
        return None


def _split_text(text: str) -> list[str]:
    """Fallback character splitter with overlap, preferring paragraph breaks."""
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + CHUNK_CHARS, n)
        # Prefer to break on a paragraph/sentence boundary near the window end.
        if end < n:
            window = text[start:end]
            for sep in ("\n\n", "\n", ". "):
                idx = window.rfind(sep)
                if idx > CHUNK_CHARS // 2:
                    end = start + idx + len(sep)
                    break
        chunks.append(text[start:end])
        if end >= n:
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return chunks
