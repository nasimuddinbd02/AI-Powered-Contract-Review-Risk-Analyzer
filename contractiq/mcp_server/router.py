"""REST endpoints for the five ContractIQ tools (SRS FR-7).

These plain FastAPI endpoints are the single source of truth for the tools. Their
Pydantic request models and docstrings are auto-converted into a real **MCP**
server by ``fastapi-mcp`` (see ``server.setup_mcp``), so the tool schemas can
never drift from the implementation. The agent layer calls the underlying
functions in ``mcp_server.tools`` directly (in-process) for efficiency.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.models import ClauseType
from .tools import (
    compare_clauses,
    extract_clauses,
    get_industry_benchmark,
    lookup_legal_definition,
    score_risk,
)

# tags=["tools"] is how ``FastApiMCP(include_tags=["tools"])`` selects exactly
# these operations to expose as MCP tools.
router = APIRouter(prefix="/tools", tags=["tools"])

_CLAUSE_ENUM = [c.value for c in ClauseType]


class ExtractClausesRequest(BaseModel):
    contract_text: str = Field(..., description="Full contract text to analyse.")


class ScoreRiskRequest(BaseModel):
    clause_text: str = Field(..., description="The clause text to score.")
    clause_type: str = Field(..., description=f"One of: {', '.join(_CLAUSE_ENUM)}.")


class LookupDefinitionRequest(BaseModel):
    term: str = Field(..., description="Legal term to define.")
    jurisdiction: str = Field("US", description="Jurisdiction context.")


class CompareClausesRequest(BaseModel):
    clause_a: str
    clause_b: str


class BenchmarkRequest(BaseModel):
    clause_type: str = Field(..., description=f"One of: {', '.join(_CLAUSE_ENUM)}.")
    industry: str = Field("general", description="Industry context.")


@router.post("/extract_clauses", operation_id="extract_clauses")
def extract_clauses_tool(body: ExtractClausesRequest) -> dict:
    """Extract and categorise the 10 standard legal clause types from contract text.

    Returns a JSON object mapping each clause type to its verbatim text (or null
    when the clause is not present).
    """
    return extract_clauses(contract_text=body.contract_text)


@router.post("/score_risk", operation_id="score_risk")
def score_risk_tool(body: ScoreRiskRequest) -> dict:
    """Score a single clause for risk: HIGH/MEDIUM/LOW, a 0-100 score, and a rationale."""
    return score_risk(clause_text=body.clause_text, clause_type=body.clause_type)


@router.post("/lookup_legal_definition", operation_id="lookup_legal_definition")
def lookup_legal_definition_tool(body: LookupDefinitionRequest) -> dict:
    """Return a plain-English definition of a legal term for the given jurisdiction."""
    return lookup_legal_definition(term=body.term, jurisdiction=body.jurisdiction)


@router.post("/compare_clauses", operation_id="compare_clauses")
def compare_clauses_tool(body: CompareClausesRequest) -> dict:
    """Compare two versions of a clause and recommend the more favourable wording."""
    return compare_clauses(clause_a=body.clause_a, clause_b=body.clause_b)


@router.post("/get_industry_benchmark", operation_id="get_industry_benchmark")
def get_industry_benchmark_tool(body: BenchmarkRequest) -> dict:
    """Return standard market language for a clause type in a given industry."""
    return get_industry_benchmark(clause_type=body.clause_type, industry=body.industry)
