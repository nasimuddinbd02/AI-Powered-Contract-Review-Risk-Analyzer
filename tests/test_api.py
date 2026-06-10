"""End-to-end API tests (SRS FR-1, FR-2, FR-6, FR-8, FR-9, 4.4 auth)."""
from __future__ import annotations

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from contractiq.api.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_mcp_server_exposes_five_tools():
    # fastapi-mcp generated a real MCP server from the /tools endpoints.
    mcp = app.state.mcp
    names = {t.name for t in mcp.tools}
    assert names == {
        "extract_clauses", "score_risk", "lookup_legal_definition",
        "compare_clauses", "get_industry_benchmark",
    }
    # Each tool advertises an input schema derived from its Pydantic model.
    score = next(t for t in mcp.tools if t.name == "score_risk")
    assert "clause_text" in score.inputSchema["properties"]


def test_tool_endpoints_callable():
    # Deterministic tool (no LLM) via the REST surface.
    r = client.post("/tools/lookup_legal_definition", json={"term": "indemnification"})
    assert r.status_code == 200, r.text
    assert r.json()["definition"]
    # LLM-backed tool runs through the fake LLM (autouse fixture).
    r = client.post("/tools/score_risk", json={
        "clause_text": "Customer accepts unlimited liability without limitation.",
        "clause_type": "Liability Cap",
    })
    assert r.status_code == 200, r.text
    assert r.json()["risk_level"] in ("HIGH", "MEDIUM", "LOW")


def test_contract_routes_require_auth():
    # Without a token, protected routes return 401.
    assert client.post("/upload").status_code == 401
    assert client.get("/contracts").status_code == 401
    assert client.post("/analyze/x").status_code == 401


def test_full_flow(sample_contract_bytes, auth_headers):
    h = auth_headers()

    # Upload
    r = client.post(
        "/upload",
        files={"file": ("sample.txt", sample_contract_bytes, "text/plain")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    cid = r.json()["contract_id"]
    assert r.json()["chunk_count"] > 0

    # Analyze
    r = client.post(f"/analyze/{cid}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "analyzed"
    assert body["clauses"]

    # Listed under the owner
    r = client.get("/contracts", headers=h)
    assert r.status_code == 200
    assert any(c["contract_id"] == cid for c in r.json())

    # Chat
    r = client.post(f"/chat/{cid}", json={"query": "What are the payment terms?"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["agent_answer"]

    # Export
    r = client.get(f"/export/{cid}", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] in ("application/pdf", "text/html; charset=utf-8")
    assert len(r.content) > 100

    # Delete (ephemeral storage)
    r = client.delete(f"/contract/{cid}", headers=h)
    assert r.status_code == 200


def test_owner_isolation(sample_contract_bytes, auth_headers):
    owner = auth_headers("a@example.com", "password123", "A")
    other = auth_headers("b@example.com", "password123", "B")
    cid = client.post(
        "/upload", files={"file": ("s.txt", sample_contract_bytes, "text/plain")}, headers=owner
    ).json()["contract_id"]
    # The other user cannot see or access it.
    assert client.get(f"/contract/{cid}", headers=other).status_code == 403
    assert client.get("/contracts", headers=other).json() == []


def test_unknown_contract_404(auth_headers):
    assert client.post("/analyze/does-not-exist", headers=auth_headers()).status_code == 404
