"""Orchestrator Agent (SRS 2.2, FR-2..FR-5).

Runs the specialist agents as a sequential state graph:

    ClauseExtractor → RiskScorer → PlainEnglish → Negotiator

Modelled on a LangGraph ``StateGraph`` (and will use LangGraph if installed),
but implemented with a dependency-light executor so it always runs. Per SRS 4.3
each node is wrapped: on failure the orchestrator logs the error, records a
warning, and continues so the user still receives partial results.
"""
from __future__ import annotations

import re

from ..core.logging import get_logger, trace
from ..core.models import Contract
from . import clause_extractor, negotiator, plain_english, risk_scorer

log = get_logger("agents.orchestrator")


class Orchestrator:
    """Sequential multi-agent pipeline over a shared :class:`Contract` state."""

    def __init__(self, contract: Contract, contract_text: str) -> None:
        self.contract = contract
        self.contract_text = contract_text

    def run(self) -> Contract:
        with trace("agent.orchestrator", contract_id=self.contract.contract_id):
            self.contract.status = "processing"
            self._detect_metadata()

            # (node name, callable). Each callable mutates and returns the contract.
            nodes = [
                ("clause_extractor", lambda c: clause_extractor.run(c, self.contract_text)),
                ("risk_scorer", risk_scorer.run),
                ("plain_english", plain_english.run),
                ("negotiator", negotiator.run),
            ]
            for name, node in nodes:
                try:
                    self.contract = node(self.contract)
                except Exception as exc:  # SRS 4.3 — partial results + warning
                    log.exception("Agent node '%s' failed", name)
                    self.contract.warnings.append(
                        f"The '{name}' step failed ({exc}); results may be incomplete."
                    )

            self.contract.status = "analyzed"
            return self.contract

    def _detect_metadata(self) -> None:
        """Lightweight detection of parties, type, and governing law (SRS 5.1)."""
        text = self.contract_text
        self.contract.parties = _detect_parties(text)
        self.contract.contract_type = _detect_type(text)
        self.contract.governing_law = _detect_governing_law(text)


def run_pipeline(contract: Contract, contract_text: str) -> Contract:
    """Convenience wrapper to run the full pipeline."""
    return Orchestrator(contract, contract_text).run()


# --- metadata heuristics ----------------------------------------------------

# DOTALL so party names can span a line break (e.g. "Acme\nCorporation").
_PARTY_RE = re.compile(
    r'(?:by and between|between)\s+(.{3,60}?)\s+(?:and|&)\s+(.{3,60}?)\s*(?:[\.,;]|\()',
    re.IGNORECASE | re.DOTALL,
)


def _detect_parties(text: str) -> list[str]:
    m = _PARTY_RE.search(text)
    if m:
        return [_clean_party(m.group(1)), _clean_party(m.group(2))]
    # Fallback: quoted defined terms like ("Company") / ("Vendor").
    quoted = re.findall(r'\(["“]([A-Z][A-Za-z ]{2,30})["”]\)', text)
    return list(dict.fromkeys(quoted))[:2]


def _clean_party(s: str) -> str:
    return re.sub(r'\s+', " ", s).strip().strip('"“”')


def _detect_type(text: str) -> str:
    low = text.lower()
    # Ordered most-specific first; keywords are document-title anchors, not
    # incidental mentions (e.g. "employee" alone must not flag an Employment
    # contract when it appears inside a non-solicit clause).
    patterns = [
        ("MSA", ["master services agreement", "statement of work"]),
        ("NDA", ["non-disclosure agreement", "nondisclosure agreement", "confidentiality agreement"]),
        ("SaaS", ["software as a service", "subscription services agreement", " saas "]),
        ("Employment", ["employment agreement", "at-will employment"]),
        ("Lease", ["lease agreement", "landlord", "tenant"]),
        ("License", ["license agreement", "licensor", "licensee"]),
    ]
    for ctype, kws in patterns:
        if any(kw in low for kw in kws):
            return ctype
    return "General Agreement"


def _detect_governing_law(text: str) -> str:
    m = re.search(r'laws of (?:the )?(?:State of |Commonwealth of )?([A-Z][A-Za-z ]{2,30})', text)
    if m:
        return _clean_party(m.group(1))
    return "Unknown"
