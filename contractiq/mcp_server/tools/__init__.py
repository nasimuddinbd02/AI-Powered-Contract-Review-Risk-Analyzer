"""MCP tool implementations.

Each tool is a plain Python function returning JSON-serialisable ``dict`` output
conforming to a defined schema (SRS FR-7). Error responses include a
human-readable ``error_message`` field. The functions are pure/deterministic so
they double as the offline fallback for the agent layer.
"""
from .extract_clauses import extract_clauses
from .score_risk import score_risk
from .lookup_legal_definition import lookup_legal_definition
from .compare_clauses import compare_clauses
from .get_industry_benchmark import get_industry_benchmark

# Registry consumed by server.py to expose tools over MCP + REST.
TOOLS = {
    "extract_clauses": extract_clauses,
    "score_risk": score_risk,
    "lookup_legal_definition": lookup_legal_definition,
    "compare_clauses": compare_clauses,
    "get_industry_benchmark": get_industry_benchmark,
}

__all__ = ["TOOLS", *TOOLS.keys()]
