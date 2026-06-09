"""Tests for the RAG layer (SRS FR-6)."""
from __future__ import annotations

from contractiq.ingestion import chunk_pages, embed_chunks, parse_pdf_bytes
from contractiq.rag import QAAgent, Retriever
from contractiq.rag.qa_agent import NO_ANSWER


def _build_qa(contract_bytes: bytes) -> QAAgent:
    pages = parse_pdf_bytes(contract_bytes, filename="sample.txt")
    chunks = chunk_pages("c1", pages)
    store = embed_chunks(chunks)
    # Use a low threshold so the mock embeddings still surface relevant chunks.
    return QAAgent(Retriever(store, threshold=0.0))


def test_qa_retrieves_and_cites(sample_contract_bytes):
    qa = _build_qa(sample_contract_bytes)
    turn = qa.ask("c1", "What are the payment terms?")
    assert turn.retrieved_chunks
    assert turn.agent_answer
    assert turn.citations


def test_qa_no_answer_above_threshold(sample_contract_bytes):
    pages = parse_pdf_bytes(sample_contract_bytes, filename="sample.txt")
    chunks = chunk_pages("c1", pages)
    store = embed_chunks(chunks)
    qa = QAAgent(Retriever(store, threshold=1.01))  # impossible threshold
    turn = qa.ask("c1", "What is the meaning of life?")
    assert turn.agent_answer == NO_ANSWER


def test_qa_history_tracked(sample_contract_bytes):
    qa = _build_qa(sample_contract_bytes)
    qa.ask("c1", "Who are the parties?")
    qa.ask("c1", "What about termination?")
    assert len(qa.history) == 2
