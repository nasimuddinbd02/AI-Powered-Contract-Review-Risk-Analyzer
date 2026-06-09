"""Ingestion layer (SRS FR-1): PDF parsing, chunking, embedding."""
from .parser import PageText, parse_pdf, parse_pdf_bytes
from .chunker import chunk_pages
from .embedder import embed_chunks

__all__ = ["PageText", "parse_pdf", "parse_pdf_bytes", "chunk_pages", "embed_chunks"]
