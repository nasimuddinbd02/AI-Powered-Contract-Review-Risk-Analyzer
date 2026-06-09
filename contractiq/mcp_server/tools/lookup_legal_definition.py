"""MCP tool: lookup_legal_definition (SRS FR-7).

Input:  term: str, jurisdiction: str
Output: JSON {definition, source}
"""
from __future__ import annotations

from ...core.logging import trace
from ...core.taxonomy import LEGAL_DEFINITIONS


def lookup_legal_definition(term: str, jurisdiction: str = "US") -> dict:
    """Return a plain-English legal definition for ``term``."""
    if not term or not term.strip():
        return {"error_message": "term is empty."}

    with trace("tool.lookup_legal_definition", term=term, jurisdiction=jurisdiction):
        key = term.strip().lower()
        definition = LEGAL_DEFINITIONS.get(key)
        if definition is None:
            # Fuzzy contains-match before giving up.
            for k, v in LEGAL_DEFINITIONS.items():
                if k in key or key in k:
                    definition, key = v, k
                    break
        if definition is None:
            return {
                "definition": None,
                "source": None,
                "error_message": f"No definition found for '{term}'.",
            }
        return {
            "term": key,
            "jurisdiction": jurisdiction,
            "definition": definition,
            "source": "ContractIQ plain-language legal glossary",
        }
