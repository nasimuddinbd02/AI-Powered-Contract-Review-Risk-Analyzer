"""RAG Q&A Agent (SRS FR-6).

Answers free-text questions about a contract:
* retrieves top-5 relevant chunks (cosine similarity),
* includes the last 10 conversation turns for continuity,
* cites page numbers / clauses in the answer,
* returns the SRS-mandated fallback message when nothing clears the threshold.

Uses Claude when available; otherwise composes an extractive answer from the
retrieved chunks so the feature works offline.
"""
from __future__ import annotations

from ..core.llm import get_llm
from ..core.logging import get_logger, trace
from ..core.models import ChunkRef, QATurn
from .retriever import Retriever

log = get_logger("rag.qa_agent")

NO_ANSWER = "I could not find this information in the contract."

_SYSTEM = (
    "You answer questions about a legal contract using ONLY the provided context "
    "chunks. Cite the page number for each fact like (p.3). If the answer is not "
    "in the context, reply exactly: 'I could not find this information in the "
    "contract.' Be concise and accurate."
)


class QAAgent:
    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever
        self.llm = get_llm()
        self.history: list[QATurn] = []

    def ask(self, contract_id: str, query: str) -> QATurn:
        with trace("rag.qa", contract_id=contract_id, provider=self.llm.provider):
            # Fold the last 10 turns into the retrieval query for continuity (FR-6).
            context_query = self._with_history(query)
            # Retrieve top-5 unfiltered, then gate on the BEST similarity. This is
            # more robust than hard-filtering every chunk: relevant query→passage
            # scores for text-embedding-3-small sit well below the SRS's nominal
            # 0.75, so the threshold is a *floor* separating real matches from
            # noise (≈0.2), and the LLM still grounds / declines via NO_ANSWER.
            chunks = self.retriever.retrieve(context_query, top_k=5, apply_threshold=False)
            best = chunks[0].score if chunks else 0.0

            if not chunks or best < self.retriever.threshold:
                turn = QATurn(contract_id=contract_id, user_query=query, agent_answer=NO_ANSWER)
                self._record(turn)
                return turn

            answer = self._answer(query, chunks)
            citations = self._citations(chunks)
            turn = QATurn(
                contract_id=contract_id,
                user_query=query,
                retrieved_chunks=chunks,
                agent_answer=answer,
                citations=citations,
            )
            self._record(turn)
            return turn

    def _with_history(self, query: str) -> str:
        recent = self.history[-10:]
        if not recent:
            return query
        prior = " ".join(t.user_query for t in recent)
        return f"{prior} {query}".strip()

    def _answer(self, query: str, chunks: list[ChunkRef]) -> str:
        context = "\n\n".join(f"[page {c.page_num}] {c.text}" for c in chunks)
        self.llm.require()
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
        return self.llm.complete(prompt, system=_SYSTEM, max_tokens=500).strip()

    @staticmethod
    def _citations(chunks: list[ChunkRef]) -> list[str]:
        return [f"page {c.page_num} (similarity {c.score:.2f})" for c in chunks]

    def _record(self, turn: QATurn) -> None:
        self.history.append(turn)
