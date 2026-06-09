"""MCP tool: get_industry_benchmark (SRS FR-7).

Input:  clause_type: str, industry: str
Output: JSON {standard_language, notes}
"""
from __future__ import annotations

from ...core.logging import trace
from ...core.models import ClauseType
from ...core.taxonomy import INDUSTRY_BENCHMARKS


def get_industry_benchmark(clause_type: str, industry: str = "general") -> dict:
    """Return standard market language for a clause type."""
    if not clause_type or not clause_type.strip():
        return {"error_message": "clause_type is required."}

    with trace("tool.get_industry_benchmark", clause_type=clause_type, industry=industry):
        try:
            ctype = ClauseType(clause_type)
        except ValueError:
            return {
                "standard_language": None,
                "notes": None,
                "error_message": (
                    f"Unknown clause_type '{clause_type}'. "
                    f"Expected one of: {', '.join(c.value for c in ClauseType)}."
                ),
            }
        return {
            "clause_type": ctype.value,
            "industry": industry,
            "standard_language": INDUSTRY_BENCHMARKS[ctype],
            "notes": f"Benchmark reflects common '{industry}' market practice; negotiate from this baseline.",
        }
