"""Retrieval + risk-scoring evaluation (SRS 4.6, FR-6 acceptance test).

Loads labelled contracts from ``evals/test_contracts/``, runs the ingestion +
RAG pipeline, and reports:

* **precision@5** — fraction of the top-5 retrieved chunks on a relevant page,
* **citation accuracy** — share of queries whose top result is on a labelled page,
* **risk-scoring accuracy** — agreement between predicted and expected risk band.

Run::

    python -m evals.eval_retrieval            # from repo root
"""
from __future__ import annotations

import json
from pathlib import Path

from contractiq.agents import run_pipeline
from contractiq.core.models import Contract
from contractiq.ingestion import chunk_pages, embed_chunks, parse_pdf_bytes
from contractiq.rag import Retriever

HERE = Path(__file__).parent
CONTRACTS = HERE / "test_contracts"


def _load_labels() -> dict:
    return json.loads((CONTRACTS / "labels.json").read_text(encoding="utf-8"))


def evaluate() -> dict:
    labels = _load_labels()
    p_at_5: list[float] = []
    citation_hits = 0
    citation_total = 0
    risk_correct = 0
    risk_total = 0

    for entry in labels["contracts"]:
        text = (CONTRACTS / entry["file"]).read_bytes()
        pages = parse_pdf_bytes(text, filename=entry["file"])
        contract = Contract(filename=entry["file"], page_count=len(pages))
        chunks = chunk_pages(contract.contract_id, pages)
        store = embed_chunks(chunks)
        # Threshold 0 so mock embeddings still surface candidates for scoring.
        retriever = Retriever(store, threshold=0.0)

        for query in entry["queries"]:
            refs = retriever.retrieve(query["q"], top_k=5)
            relevant = set(query["relevant_pages"])
            if refs:
                hits = sum(1 for r in refs if r.page_num in relevant)
                p_at_5.append(hits / len(refs))
                citation_total += 1
                if refs[0].page_num in relevant:
                    citation_hits += 1

        # Risk-band accuracy.
        analyzed = run_pipeline(contract, "\n\n".join(p.text for p in pages))
        predicted = {c.clause_type.value: (c.risk_level.value if c.risk_level else None)
                     for c in analyzed.clauses}
        for ctype, expected in entry.get("risk_levels", {}).items():
            risk_total += 1
            if predicted.get(ctype) == expected:
                risk_correct += 1

    results = {
        "contracts_evaluated": len(labels["contracts"]),
        "precision_at_5": round(sum(p_at_5) / len(p_at_5), 3) if p_at_5 else 0.0,
        "citation_accuracy": round(citation_hits / citation_total, 3) if citation_total else 0.0,
        "risk_scoring_accuracy": round(risk_correct / risk_total, 3) if risk_total else 0.0,
    }
    return results


if __name__ == "__main__":
    res = evaluate()
    print("\n=== ContractIQ Evaluation (SRS 4.6) ===")
    for k, v in res.items():
        print(f"  {k:24} {v}")
    print("\nTargets (SRS FR-6 acceptance): precision@5 >= 0.85, citation accuracy >= 0.90")
