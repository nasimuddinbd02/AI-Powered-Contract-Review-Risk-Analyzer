"""Tests for the ingestion pipeline (SRS FR-1)."""
from __future__ import annotations

from contractiq.ingestion import chunk_pages, embed_chunks, parse_pdf_bytes


def test_parse_text_fallback(sample_contract_bytes):
    pages = parse_pdf_bytes(sample_contract_bytes, filename="sample.txt")
    assert pages
    assert "CONFIDENTIALITY" in " ".join(p.text for p in pages)


def test_chunking_produces_chunks(sample_contract_bytes):
    pages = parse_pdf_bytes(sample_contract_bytes, filename="sample.txt")
    chunks = chunk_pages("c1", pages)
    assert chunks
    assert all(c.contract_id == "c1" for c in chunks)
    assert all(c.text for c in chunks)


def test_embedding_populates_store(sample_contract_bytes):
    pages = parse_pdf_bytes(sample_contract_bytes, filename="sample.txt")
    chunks = chunk_pages("c1", pages)
    store = embed_chunks(chunks)
    assert len(store.chunks) == len(chunks)
    assert all(c.embedding is not None for c in chunks)
