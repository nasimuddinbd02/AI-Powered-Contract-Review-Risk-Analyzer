"""MCP tool: compare_clauses (SRS FR-7).

Input:  clause_a: str, clause_b: str
Output: JSON {differences, recommendation}
"""
from __future__ import annotations

import difflib
import re

from ...core.logging import trace

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def compare_clauses(clause_a: str, clause_b: str) -> dict:
    """Compare two versions of a clause and recommend which is more favourable."""
    if not clause_a or not clause_b:
        return {"error_message": "Both clause_a and clause_b are required."}

    with trace("tool.compare_clauses"):
        a_tokens, b_tokens = _tokens(clause_a), _tokens(clause_b)
        sm = difflib.SequenceMatcher(a=a_tokens, b=b_tokens)
        ratio = round(sm.ratio(), 3)

        added, removed = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "delete"):
                removed.extend(a_tokens[i1:i2])
            if tag in ("replace", "insert"):
                added.extend(b_tokens[j1:j2])

        from ...core.taxonomy import HIGH_RISK_SIGNALS

        a_risky = sum(s in clause_a.lower() for s in HIGH_RISK_SIGNALS)
        b_risky = sum(s in clause_b.lower() for s in HIGH_RISK_SIGNALS)
        if a_risky < b_risky:
            rec = "Clause A is more favourable (fewer high-risk terms)."
        elif b_risky < a_risky:
            rec = "Clause B is more favourable (fewer high-risk terms)."
        else:
            rec = "Both clauses carry comparable risk; choose based on specific terms."

        return {
            "similarity": ratio,
            "differences": {
                "added_in_b": added[:50],
                "removed_from_a": removed[:50],
            },
            "risk_signal_count": {"clause_a": a_risky, "clause_b": b_risky},
            "recommendation": rec,
        }
