"""Clause Extractor Agent (SRS FR-2).

Calls the MCP tool ``extract_clauses`` and materialises ``Clause`` objects.
Absent clause types are skipped (the tool returns null — no hallucination).
"""
from __future__ import annotations

from ..core.logging import get_logger, trace
from ..core.models import Clause, ClauseType, Contract
from ..mcp_server.tools import extract_clauses

log = get_logger("agents.clause_extractor")


def run(contract: Contract, contract_text: str) -> Contract:
    """Populate ``contract.clauses`` from the contract text."""
    with trace("agent.clause_extractor", contract_id=contract.contract_id):
        result = extract_clauses(contract_text=contract_text)
        if "error_message" in result:
            contract.warnings.append(f"Clause extraction: {result['error_message']}")
            return contract

        clauses: list[Clause] = []
        for ctype in ClauseType:
            entry = result.get(ctype.value)
            if not entry:  # null → clause absent
                continue
            clauses.append(
                Clause(
                    contract_id=contract.contract_id,
                    clause_type=ctype,
                    original_text=entry["clause_text"],
                    page_references=entry.get("page_references", []),
                )
            )
        contract.clauses = clauses
        log.info("Extracted %d/%d clause types", len(clauses), len(ClauseType))
        return contract
