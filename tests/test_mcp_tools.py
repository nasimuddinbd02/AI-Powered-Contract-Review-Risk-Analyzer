"""Tests for MCP tools (SRS FR-7)."""
from __future__ import annotations

from contractiq.mcp_server.tools import (
    compare_clauses,
    extract_clauses,
    get_industry_benchmark,
    lookup_legal_definition,
    score_risk,
)


def test_extract_clauses_finds_majority(sample_contract_text):
    result = extract_clauses(contract_text=sample_contract_text)
    found = [k for k, v in result.items() if v]
    # Acceptance: >= 8 of 10 clause types identified (SRS FR-2 acceptance test).
    assert len(found) >= 8, f"only found {found}"


def test_extract_clauses_absent_is_null():
    result = extract_clauses(contract_text="This document only discusses the weather. " * 5)
    assert all(v is None for v in result.values())


def test_score_risk_bands():
    high = score_risk(clause_text="Customer accepts unlimited liability without limitation.",
                      clause_type="Liability Cap")
    assert high["risk_level"] == "HIGH"
    assert 0 <= high["score"] <= 100
    low = score_risk(clause_text="Standard governing law of Delaware applies.",
                     clause_type="Governing Law")
    assert low["risk_level"] in ("LOW", "MEDIUM")


def test_score_risk_empty():
    assert "error_message" in score_risk(clause_text="", clause_type="Termination")


def test_lookup_legal_definition():
    out = lookup_legal_definition(term="indemnification")
    assert out["definition"]
    miss = lookup_legal_definition(term="zzz-not-a-term")
    assert "error_message" in miss


def test_compare_clauses():
    out = compare_clauses(clause_a="Liability is capped at fees paid.",
                          clause_b="Customer accepts unlimited liability without limitation.")
    assert "recommendation" in out
    assert out["risk_signal_count"]["clause_b"] >= out["risk_signal_count"]["clause_a"]


def test_get_industry_benchmark():
    out = get_industry_benchmark(clause_type="Termination", industry="saas")
    assert out["standard_language"]
    bad = get_industry_benchmark(clause_type="Nonsense")
    assert "error_message" in bad
