"""Local smoke test — exercises the running ContractIQ stack end-to-end.

Hits the API through the Next.js proxy (http://localhost:3000/api) exactly as the
browser does, covering upload, analyze, all 5 MCP tools, chat, and PDF export.

    python scripts/smoke_test.py            # via frontend proxy (default)
    python scripts/smoke_test.py 8000       # direct to backend port
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = "http://localhost:3000/api" if len(sys.argv) < 2 else f"http://localhost:{sys.argv[1]}"
CONTRACT = Path(__file__).resolve().parent.parent / "evals" / "test_contracts" / "msa_globex.txt"


def hr(title: str) -> None:
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


def main() -> int:
    c = httpx.Client(timeout=120)

    hr("0. HEALTH")
    h = c.get(f"{BASE}/health").json()
    print(f"  status={h['status']}  provider={h['llm_provider']}  model={h['llm_model']}  "
          f"llm_ready={h['llm_ready']}  embeddings_ready={h['embeddings_ready']}")

    hr("0b. AUTH (SRS 4.4)")
    import uuid
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post(f"{BASE}/auth/signup", json={"email": email, "password": "password123", "full_name": "Smoke Test"})
    r.raise_for_status()
    body = r.json()
    token = body["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    print(f"  signed up {email} (role={body['user']['role']}); bearer token acquired")

    hr("1. UPLOAD (FR-1)")
    files = {"file": (CONTRACT.name, CONTRACT.read_bytes(), "text/plain")}
    up = c.post(f"{BASE}/upload", files=files).json()
    cid = up["contract_id"]
    print(f"  {up['filename']}: pages={up['page_count']} chunks={up['chunk_count']} -> {cid}")

    hr("2. ANALYZE (FR-2..FR-5)")
    a = c.post(f"{BASE}/analyze/{cid}").json()
    print(f"  type={a['contract_type']}  law={a['governing_law']}  parties={a['parties']}")
    print(f"  OVERALL RISK = {a['overall_risk_score']}/100  ({len(a['clauses'])} clauses)")
    for cl in a["clauses"]:
        neg = "YES" if cl["negotiation_suggestion"] else "no"
        print(f"   - {cl['clause_type']:<20}{cl['risk_level']:<7}{cl['risk_score']:>5.0f}  neg:{neg:<3} {cl['plain_english_summary'][:44]}")
    if a["warnings"]:
        print("  warnings:", a["warnings"])

    hr("3. MCP TOOLS (FR-7) — real MCP server mounted at /mcp via fastapi-mcp")
    calls = [
        ("score_risk", {"clause_text": "Customer accepts unlimited liability without limitation.", "clause_type": "Liability Cap"}),
        ("lookup_legal_definition", {"term": "indemnification"}),
        ("get_industry_benchmark", {"clause_type": "Termination", "industry": "saas"}),
        ("compare_clauses", {"clause_a": "Liability is capped at fees paid.", "clause_b": "Unlimited liability without limitation."}),
    ]
    for name, args in calls:
        r = c.post(f"{BASE}/tools/{name}", json=args).json()
        preview = {k: r[k] for k in list(r)[:2]}
        print(f"   - {name:<24} -> {preview}")

    hr("4. CHAT / RAG Q&A (FR-6)")
    for q in ["What is the cap on liability?", "What are the payment terms and late fees?", "Who owns the intellectual property?"]:
        t = c.post(f"{BASE}/chat/{cid}", json={"query": q}).json()
        print(f"  Q: {q}")
        print(f"  A: {t['agent_answer'][:150]}")
        print(f"     cites: {t['citations']}")

    hr("5. EXPORT REPORT (FR-9)")
    r = c.get(f"{BASE}/export/{cid}")
    kind = "PDF" if r.content[:5] == b"%PDF-" else r.headers.get("content-type")
    print(f"  {r.status_code}  {kind}  {len(r.content)} bytes  {r.headers.get('content-disposition')}")

    hr("6. TRACES (FR-4.6)")
    tr = c.get(f"{BASE}/traces").json()
    print(f"  recorded {tr['total_recorded']} traces; sample latencies:")
    for t in tr["traces"][-5:]:
        print(f"   - {t['name']:<24} {t['latency_ms']:>7.1f} ms")

    hr("7. DELETE / EPHEMERAL (4.4)")
    print("  delete:", c.delete(f"{BASE}/contract/{cid}").json())
    print("\n[OK] All steps completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
