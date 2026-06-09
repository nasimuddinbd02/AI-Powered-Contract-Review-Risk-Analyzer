"""Negotiation Agent (SRS FR-5) — LLM-powered.

For every HIGH or MEDIUM risk clause, suggests revised counter-language with a
one-sentence justification, grounded in the industry-benchmark MCP tool.
"""
from __future__ import annotations

from ..core.llm import get_llm
from ..core.logging import get_logger, trace
from ..core.models import Contract, RiskLevel
from ..mcp_server.tools import get_industry_benchmark

log = get_logger("agents.negotiator")

_SYSTEM = (
    "You are a contract negotiation assistant protecting the reader. Given a risky "
    "clause and an industry-standard baseline, propose balanced counter-language and "
    "a one-sentence justification. Return STRICT JSON: "
    '{"suggested_language": <string>, "justification": <string>}. Output JSON only.'
)


def run(contract: Contract) -> Contract:
    """Attach ``negotiation_suggestion`` to each HIGH/MEDIUM risk clause."""
    llm = get_llm()
    with trace("agent.negotiator", contract_id=contract.contract_id, provider=llm.provider):
        for clause in contract.clauses:
            if clause.risk_level not in (RiskLevel.HIGH, RiskLevel.MEDIUM):
                continue  # null suggestion for Low risk (SRS 5.2)
            clause.negotiation_suggestion = _suggest(clause, llm)
        return contract


def _suggest(clause, llm) -> str | None:
    benchmark = get_industry_benchmark(clause_type=clause.clause_type.value)
    standard = benchmark.get("standard_language", "")
    try:
        llm.require()
        prompt = (
            f"Clause type: {clause.clause_type.value}\n"
            f"Risk level: {clause.risk_level.value}\n"
            f"Original clause:\n{clause.original_text[:1500]}\n\n"
            f"Industry-standard baseline: {standard}"
        )
        data = llm.complete_json(prompt, system=_SYSTEM, max_tokens=400)
        return f"{data['suggested_language']} — {data['justification']}"
    except Exception as exc:
        log.warning("Negotiation suggestion failed for %s: %s", clause.clause_type.value, exc)
        return None
