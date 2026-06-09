"""MCP tool: extract_clauses (SRS FR-7 / FR-2) — LLM-powered.

Input:  contract_text: str
Output: JSON dict mapping clause_type -> {clause_text, page_references} (or null)

Uses the configured LLM to identify the 10 standard clause types, returning the
verbatim clause text. Absent clauses map to ``null`` (no hallucination, FR-2).
Page references are recovered by locating each clause in the page-marked text.
"""
from __future__ import annotations

import re

from ...core.llm import get_llm
from ...core.logging import trace
from ...core.models import ClauseType

_PAGE_RE = re.compile(r"\[\[page=(\d+)\]\]")
_CLAUSE_TYPES = [c.value for c in ClauseType]

_SYSTEM = (
    "You are a contract analysis engine. Extract standard legal clauses from the "
    "provided contract text. Return STRICT JSON: an object whose keys are exactly "
    f"these clause types: {_CLAUSE_TYPES}. For each key, the value is either the "
    "verbatim clause text (a string copied from the contract) or null if that "
    "clause type is not present. Do not invent or paraphrase text. Output JSON only."
)


def _page_for(snippet: str, marked_text: str) -> list[int]:
    """Find page numbers for a clause by locating its text in the marked source."""
    probe = re.sub(r"\s+", " ", snippet[:60]).strip()
    if not probe:
        return []
    clean = re.sub(r"\s+", " ", _PAGE_RE.sub("", marked_text))
    idx = clean.find(probe)
    if idx < 0:
        return []
    # Map char offset back to the nearest preceding page marker.
    pages = [(m.start(), int(m.group(1))) for m in _PAGE_RE.finditer(marked_text)]
    # Approximate: count marker order by char position in the *unstripped* text.
    page = 1
    running = 0
    for _, pno in pages:
        page = pno
        running += 1
        if running * (len(clean) // max(len(pages), 1) or 1) > idx:
            break
    return [page]


def extract_clauses(contract_text: str) -> dict:
    """Extract and categorise legal clauses from raw contract text (LLM)."""
    if not contract_text or not contract_text.strip():
        return {"error_message": "contract_text is empty."}

    llm = get_llm()
    with trace("tool.extract_clauses", chars=len(contract_text)):
        try:
            llm.require()
            data = llm.complete_json(
                f"Contract text:\n{contract_text[:18000]}",
                system=_SYSTEM,
                max_tokens=3000,
            )
        except Exception as exc:
            return {"error_message": f"extract_clauses failed: {exc}"}

        result: dict[str, dict | None] = {}
        for ctype in ClauseType:
            text = data.get(ctype.value) if isinstance(data, dict) else None
            if isinstance(text, str) and text.strip():
                result[ctype.value] = {
                    "clause_text": text.strip()[:2000],
                    "page_references": _page_for(text, contract_text),
                }
            else:
                result[ctype.value] = None
        return result
