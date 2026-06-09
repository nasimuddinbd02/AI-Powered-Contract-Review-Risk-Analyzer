"""Plain-English Agent (SRS FR-4) — LLM-powered.

Produces a one-sentence (<=30-word), ~8th-grade-reading-level summary per clause
and flags clauses whose meaning is ambiguous, in a single batched LLM call.
"""
from __future__ import annotations

import re

from ..core.llm import get_llm
from ..core.logging import get_logger, trace
from ..core.models import Contract

log = get_logger("agents.plain_english")

_SYSTEM = (
    "You rewrite legal contract clauses into plain English. For each clause you "
    "are given, produce ONE sentence of at most 30 words at an 8th-grade reading "
    "level that explains what it means for the reader. If a clause's meaning is "
    "ambiguous or unclear, set \"ambiguous\": true and start the summary with "
    "'Unclear:'. Return STRICT JSON: an array of objects "
    '{"index": <int>, "summary": <string>, "ambiguous": <bool>} in input order. '
    "Output JSON only."
)


def _truncate_words(text: str, limit: int = 30) -> str:
    words = text.split()
    return text if len(words) <= limit else " ".join(words[:limit]).rstrip(",.;") + "."


def run(contract: Contract) -> Contract:
    """Add ``plain_english_summary`` and ``is_ambiguous`` to each clause."""
    llm = get_llm()
    if not contract.clauses:
        return contract
    with trace("agent.plain_english", contract_id=contract.contract_id, provider=llm.provider):
        llm.require()
        numbered = "\n\n".join(
            f"[{i}] ({c.clause_type.value}) {c.original_text[:1200]}"
            for i, c in enumerate(contract.clauses)
        )
        data = llm.complete_json(
            f"Clauses to summarise:\n{numbered}", system=_SYSTEM, max_tokens=1500
        )
        by_index = {int(item["index"]): item for item in data if isinstance(item, dict) and "index" in item}
        for i, clause in enumerate(contract.clauses):
            item = by_index.get(i, {})
            summary = re.sub(r"\s+", " ", str(item.get("summary", ""))).strip()
            clause.plain_english_summary = _truncate_words(summary) if summary else None
            clause.is_ambiguous = bool(item.get("ambiguous")) or summary.lower().startswith("unclear:")
        return contract
