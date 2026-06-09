"""MCP tool: score_risk (SRS FR-7 / FR-3) — LLM-powered.

Input:  clause_text: str, clause_type: str
Output: JSON {risk_level, score, rationale}

Uses the LLM to assess a single clause from the perspective of the party
reviewing the contract, returning a HIGH/MEDIUM/LOW band, a 0-100 score, and a
concise rationale (surfaced in the UI tooltip, SRS FR-3).
"""
from __future__ import annotations

from ...core.llm import get_llm
from ...core.logging import trace

_SYSTEM = (
    "You are a contract risk assessor protecting the party reviewing this contract. "
    "Score ONE clause for risk. Return STRICT JSON: "
    '{"risk_level": "HIGH"|"MEDIUM"|"LOW", "score": <0-100 integer>, '
    '"rationale": "<one or two sentences explaining the risk>"}. '
    "HIGH (67-100) = significantly disadvantages the reviewer / needs immediate review; "
    "MEDIUM (34-66) = non-standard terms worth negotiating; "
    "LOW (0-33) = standard, minimal risk. Output JSON only."
)

_VALID = {"HIGH", "MEDIUM", "LOW"}


def score_risk(clause_text: str, clause_type: str) -> dict:
    """Score a single clause for risk (LLM)."""
    if not clause_text or not clause_text.strip():
        return {"error_message": "clause_text is empty."}

    llm = get_llm()
    with trace("tool.score_risk", clause_type=clause_type):
        try:
            llm.require()
            data = llm.complete_json(
                f"Clause type: {clause_type}\nClause text:\n{clause_text[:4000]}",
                system=_SYSTEM,
                max_tokens=400,
            )
        except Exception as exc:
            return {"error_message": f"score_risk failed: {exc}"}

        level = str(data.get("risk_level", "")).upper()
        if level not in _VALID:
            return {"error_message": f"Invalid risk_level from model: {level!r}"}
        try:
            score = float(data.get("score", 0))
        except (TypeError, ValueError):
            score = {"HIGH": 80.0, "MEDIUM": 50.0, "LOW": 15.0}[level]
        score = max(0.0, min(100.0, score))
        return {
            "risk_level": level,
            "score": round(score, 1),
            "rationale": str(data.get("rationale", "")).strip(),
        }
