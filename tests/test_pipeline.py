"""Tests for the multi-agent pipeline (SRS FR-2..FR-5)."""
from __future__ import annotations

from contractiq.agents import run_pipeline
from contractiq.core.models import Contract, RiskLevel


def test_full_pipeline(sample_contract_text):
    contract = Contract(filename="sample.pdf")
    result = run_pipeline(contract, sample_contract_text)

    assert result.status == "analyzed"
    assert result.clauses, "pipeline should extract clauses"
    assert 0 <= result.overall_risk_score <= 100

    for clause in result.clauses:
        assert clause.risk_level is not None
        assert clause.risk_score is not None
        assert clause.plain_english_summary
        # Plain-English summaries are <= 30 words (SRS FR-4).
        assert len(clause.plain_english_summary.split()) <= 31

    # Negotiation suggestions only for HIGH/MEDIUM (SRS FR-5 / 5.2).
    for clause in result.clauses:
        if clause.risk_level == RiskLevel.LOW:
            assert clause.negotiation_suggestion is None
        else:
            assert clause.negotiation_suggestion


def test_pipeline_detects_metadata(sample_contract_text):
    contract = Contract(filename="sample.pdf")
    result = run_pipeline(contract, sample_contract_text)
    assert result.contract_type in ("MSA", "General Agreement", "NDA", "SaaS")
    assert "Delaware" in result.governing_law


def test_party_detection_across_linebreak():
    # Regression: party names that span a line break must still be detected
    # (the "by and between Acme\nCorporation and Globex LLC" case).
    text = (
        'This Master Services Agreement is made by and between Acme\n'
        'Corporation and Globex LLC ("Vendor"), effective January 1, 2026.'
    )
    result = run_pipeline(Contract(filename="x.pdf"), text)
    assert result.parties == ["Acme Corporation", "Globex LLC"]
