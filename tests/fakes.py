"""Test doubles for the LLM and embedding clients.

These let the suite run offline and deterministically without an API key or
network. They are TEST infrastructure only — the application itself has no mock
path (it requires a real OpenAI/Anthropic key). The autouse fixture in
``conftest.py`` installs them unless ``CONTRACTIQ_LIVE_TESTS=1`` is set.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from contractiq.core.embeddings import EMBED_DIM
from contractiq.core.models import ClauseType
from contractiq.core.taxonomy import CLAUSE_KEYWORDS, HIGH_RISK_SIGNALS, MEDIUM_RISK_SIGNALS

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_PAGE_RE = re.compile(r"\[\[page=\d+\]\]")


# --------------------------------------------------------------------------- #
# Fake LLM
# --------------------------------------------------------------------------- #
class FakeLLM:
    """Deterministic stand-in for ``LLMClient`` that routes by system prompt."""

    provider = "fake"
    model = "fake-model"
    available = True

    def require(self) -> None:  # always "configured"
        return None

    def complete(self, prompt: str, system: str = "", **_) -> str:
        if "Extract standard legal clauses" in system:
            return json.dumps(self._extract(prompt))
        if "Score ONE clause" in system:
            return json.dumps(self._score(prompt))
        if "rewrite legal contract clauses" in system:
            return json.dumps(self._summaries(prompt))
        if "negotiation assistant" in system:
            return json.dumps(self._negotiate(prompt))
        if "answer questions about a legal contract" in system:
            return self._qa(prompt)
        return "{}"

    def complete_json(self, prompt: str, system: str = "", **kw):
        from contractiq.core.llm import extract_json

        return extract_json(self.complete(prompt, system=system, **kw))

    # --- routed implementations ---
    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        text = _PAGE_RE.sub("", text)
        return [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 25]

    def _extract(self, prompt: str) -> dict:
        paras = self._paragraphs(prompt)
        out: dict[str, str | None] = {}
        for ctype in ClauseType:
            kws = CLAUSE_KEYWORDS[ctype]
            best, best_score = None, 0
            for p in paras:
                low = p.lower()
                score = sum(low.count(k) for k in kws)
                if score > best_score:
                    best, best_score = p, score
            out[ctype.value] = best if best_score > 0 else None
        return out

    def _score(self, prompt: str) -> dict:
        low = prompt.lower()
        base = 30
        hi = [s for s in HIGH_RISK_SIGNALS if s in low]
        med = [s for s in MEDIUM_RISK_SIGNALS if s in low]
        score = min(100, base + 22 * len(hi) + 7 * len(med))
        level = "HIGH" if score >= 67 else "MEDIUM" if score >= 34 else "LOW"
        return {"risk_level": level, "score": score, "rationale": f"Heuristic fake score ({level})."}

    def _summaries(self, prompt: str) -> list:
        items = []
        for m in re.finditer(r"\[(\d+)\]\s*\(([^)]+)\)", prompt):
            idx = int(m.group(1))
            ctype = m.group(2)
            items.append({"index": idx, "summary": f"This {ctype} clause sets out key terms in plain language.", "ambiguous": False})
        return items

    def _negotiate(self, _prompt: str) -> dict:
        return {"suggested_language": "Propose balanced, market-standard language.",
                "justification": "Aligns the clause with common practice and reduces risk."}

    def _qa(self, prompt: str) -> str:
        q = prompt.split("Question:")[-1]
        terms = {w for w in _TOKEN_RE.findall(q.lower()) if len(w) > 3}
        context = prompt.split("Question:")[0]
        best, best_overlap, page = "", 0, 1
        for line in re.split(r"(?<=[.;])\s+|\n+", context):
            s = line.strip()
            if len(s) < 20:
                continue
            overlap = sum(1 for t in terms if t in s.lower())
            if overlap > best_overlap:
                best, best_overlap = s, overlap
                pm = re.search(r"\[page (\d+)\]", line)
                if pm:
                    page = int(pm.group(1))
        if not best:
            return "I could not find this information in the contract."
        clean = re.sub(r"\[page \d+\]", "", best).strip()
        return f"{clean} (p.{page})"


# --------------------------------------------------------------------------- #
# Fake embeddings
# --------------------------------------------------------------------------- #
class FakeEmbedder:
    """Deterministic hashed bag-of-words embeddings (unit length)."""

    model = "fake-embeddings"
    available = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._one(text)

    @staticmethod
    def _one(text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        for tok in _TOKEN_RE.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % EMBED_DIM] += 1.0 if (h >> 8) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec
