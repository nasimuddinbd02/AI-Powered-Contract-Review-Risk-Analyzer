"""Application service layer — orchestrates ingestion, analysis, and Q&A.

Holds per-contract sessions in memory only (SRS 4.4: ephemeral storage, no
persistence of contract text without consent). A ``ContractSession`` bundles the
contract metadata, its vector store, and a stateful Q&A agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .agents import run_pipeline
from .core.logging import get_logger
from .core.models import Contract, QATurn
from .core.vector_store import VectorStore
from .ingestion import chunk_pages, embed_chunks, parse_pdf_bytes
from .ingestion.parser import PageText
from .rag import QAAgent, Retriever

log = get_logger("service")


@dataclass
class ContractSession:
    contract: Contract
    store: VectorStore
    full_text: str
    qa_agent: QAAgent
    owner_id: str
    pages: list[PageText] = field(default_factory=list)


class AccessDenied(Exception):
    """Raised when a user accesses a contract they do not own."""


class SessionManager:
    """In-memory registry of active contract sessions, scoped per owner."""

    def __init__(self) -> None:
        self._sessions: dict[str, ContractSession] = {}

    # --- ingestion (SRS FR-1) ---
    def ingest(self, data: bytes, filename: str, owner_id: str) -> Contract:
        pages = parse_pdf_bytes(data, filename=filename)
        contract = Contract(filename=filename, page_count=len(pages))

        chunks = chunk_pages(contract.contract_id, pages)
        contract.chunk_count = len(chunks)
        store = embed_chunks(chunks)

        retriever = Retriever(store)
        session = ContractSession(
            contract=contract,
            store=store,
            full_text=_pages_to_text(pages),
            qa_agent=QAAgent(retriever),
            owner_id=owner_id,
            pages=pages,
        )
        self._sessions[contract.contract_id] = session
        log.info("Ingested '%s' as %s for user %s (%d pages, %d chunks)",
                 filename, contract.contract_id, owner_id, len(pages), len(chunks))
        return contract

    # --- analysis (SRS FR-2..FR-5) ---
    def analyze(self, contract_id: str, owner_id: str, is_admin: bool = False) -> Contract:
        session = self.get(contract_id, owner_id, is_admin)
        session.contract = run_pipeline(session.contract, session.full_text)
        return session.contract

    # --- Q&A (SRS FR-6) ---
    def ask(self, contract_id: str, query: str, owner_id: str, is_admin: bool = False) -> QATurn:
        session = self.get(contract_id, owner_id, is_admin)
        return session.qa_agent.ask(contract_id, query)

    def get(self, contract_id: str, owner_id: str, is_admin: bool = False) -> ContractSession:
        if contract_id not in self._sessions:
            raise KeyError(f"Unknown contract_id: {contract_id}")
        session = self._sessions[contract_id]
        if not is_admin and session.owner_id != owner_id:
            raise AccessDenied(contract_id)
        return session

    def get_contract(self, contract_id: str, owner_id: str, is_admin: bool = False) -> Contract:
        return self.get(contract_id, owner_id, is_admin).contract

    def list_for_owner(self, owner_id: str, is_admin: bool = False) -> list[Contract]:
        return [
            s.contract for s in self._sessions.values()
            if is_admin or s.owner_id == owner_id
        ]

    def delete(self, contract_id: str, owner_id: str, is_admin: bool = False) -> None:
        """Purge a session and its contract text from memory (SRS 4.4)."""
        if contract_id in self._sessions:
            self.get(contract_id, owner_id, is_admin)  # access check
            self._sessions.pop(contract_id, None)


def _pages_to_text(pages: list[PageText]) -> str:
    """Join pages, embedding page markers so clause extraction can cite pages."""
    return "\n\n".join(f"[[page={p.page_num}]]\n{p.text}" for p in pages)


# Process-wide singleton used by the API routes.
sessions = SessionManager()
