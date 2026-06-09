"""JSON schemas for MCP tool inputs (SRS FR-7).

Used both to advertise tools over the MCP protocol and to validate REST calls.
"""
from __future__ import annotations

from ..core.models import ClauseType

_CLAUSE_ENUM = [c.value for c in ClauseType]

TOOL_SCHEMAS: dict[str, dict] = {
    "extract_clauses": {
        "description": "Extracts and categorizes legal clauses from full contract text.",
        "input_schema": {
            "type": "object",
            "properties": {"contract_text": {"type": "string"}},
            "required": ["contract_text"],
        },
    },
    "score_risk": {
        "description": "Scores a single clause for risk (HIGH/MEDIUM/LOW + 0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "clause_text": {"type": "string"},
                "clause_type": {"type": "string", "enum": _CLAUSE_ENUM},
            },
            "required": ["clause_text", "clause_type"],
        },
    },
    "lookup_legal_definition": {
        "description": "Returns a plain-English legal definition for a term.",
        "input_schema": {
            "type": "object",
            "properties": {
                "term": {"type": "string"},
                "jurisdiction": {"type": "string", "default": "US"},
            },
            "required": ["term"],
        },
    },
    "compare_clauses": {
        "description": "Compares two versions of a clause and recommends the more favourable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clause_a": {"type": "string"},
                "clause_b": {"type": "string"},
            },
            "required": ["clause_a", "clause_b"],
        },
    },
    "get_industry_benchmark": {
        "description": "Returns standard market language for a clause type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clause_type": {"type": "string", "enum": _CLAUSE_ENUM},
                "industry": {"type": "string", "default": "general"},
            },
            "required": ["clause_type"],
        },
    },
}
