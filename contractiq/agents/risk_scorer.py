"""Risk Scorer Agent (SRS FR-3).

Scores each clause via the MCP ``score_risk`` tool and computes the overall
contract risk score as a weighted average (weights from SRS Appendix B).
"""
from __future__ import annotations

from ..core.logging import get_logger, trace
from ..core.models import Contract, RiskLevel
from ..core.taxonomy import RISK_WEIGHTS
from ..mcp_server.tools import score_risk

log = get_logger("agents.risk_scorer")


def run(contract: Contract) -> Contract:
    """Assign risk level/score/rationale to each clause and roll up an overall score."""
    with trace("agent.risk_scorer", contract_id=contract.contract_id):
        for clause in contract.clauses:
            res = score_risk(clause_text=clause.original_text, clause_type=clause.clause_type.value)
            if "error_message" in res:
                contract.warnings.append(
                    f"Risk scoring {clause.clause_type.value}: {res['error_message']}"
                )
                continue
            clause.risk_level = RiskLevel(res["risk_level"])
            clause.risk_score = res["score"]
            clause.risk_rationale = res["rationale"]

        contract.overall_risk_score = _weighted_overall(contract)
        log.info("Overall risk score: %.1f", contract.overall_risk_score)
        return contract


def _weighted_overall(contract: Contract) -> float:
    """Weighted average of clause scores using Appendix B weights."""
    num = 0.0
    denom = 0.0
    for clause in contract.clauses:
        if clause.risk_score is None:
            continue
        weight = RISK_WEIGHTS.get(clause.clause_type, 0.0)
        num += weight * clause.risk_score
        denom += weight
    if denom == 0:
        return 0.0
    return round(num / denom, 1)
