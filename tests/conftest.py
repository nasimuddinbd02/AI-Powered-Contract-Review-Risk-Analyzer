"""Shared pytest fixtures: a representative sample contract + AI test doubles."""
from __future__ import annotations

import os

import pytest

import contractiq.core.embeddings as _emb
import contractiq.core.llm as _llm
from contractiq.auth.store import reset_user_store
from tests.fakes import FakeEmbedder, FakeLLM


@pytest.fixture(autouse=True)
def ai_fakes():
    """Install deterministic fake LLM + embedder for every test, and isolate the
    user store in an in-memory SQLite DB so auth tests don't touch real data.

    Set ``CONTRACTIQ_LIVE_TESTS=1`` to run against the real configured providers
    instead (requires OPENAI_API_KEY). The application has no mock path; these
    doubles exist only so the suite runs offline and deterministically.
    """
    reset_user_store(":memory:")  # fresh, empty user table per test
    if os.getenv("CONTRACTIQ_LIVE_TESTS") == "1":
        yield
    else:
        _llm._client = FakeLLM()
        _emb._client = FakeEmbedder()
        try:
            yield
        finally:
            _llm.reset_llm()
            _emb.reset_embedder()


@pytest.fixture
def auth_headers():
    """Factory: create a user via the API and return its bearer auth headers."""
    from contractiq.api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    def _make(email: str = "owner@example.com", password: str = "password123", full_name: str = "Owner"):
        r = client.post("/auth/signup", json={"email": email, "password": password, "full_name": full_name})
        assert r.status_code in (201, 409), r.text
        if r.status_code == 409:
            r = client.post("/auth/login", json={"email": email, "password": password})
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make

SAMPLE_CONTRACT = """\
MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is made by and between Acme Corporation
and Globex LLC ("Vendor"), effective as of January 1, 2026.

1. CONFIDENTIALITY
Each party shall keep confidential all proprietary information and trade secrets
disclosed under this Agreement and shall not disclose such confidential information
to any third party for a period of five years.

2. PAYMENT TERMS
Customer shall pay all invoices net 30 days. Late payments shall accrue a penalty
and late fee of 1.5% per month on any overdue amount.

3. LIMITATION OF LIABILITY
In no event shall Vendor's aggregate liability exceed the fees paid in the prior
twelve months. Notwithstanding the foregoing, Customer accepts unlimited liability
for any breach of confidentiality, without limitation.

4. INDEMNIFICATION
Customer shall indemnify and hold harmless Vendor from any and all claims, including
claims arising from Customer's use of the services, in Vendor's sole discretion.

5. INTELLECTUAL PROPERTY
All work product and intellectual property created under this Agreement shall be
owned exclusively by Vendor, who assigns all right, title, and interest irrevocably.

6. TERMINATION
Either party may terminate this Agreement for cause upon 30 days written notice.
Vendor may terminate without notice if Customer breaches any term.

7. NON-COMPETE
Customer shall not compete with Vendor or solicit Vendor's employees for a period
of two years following termination of this Agreement.

8. AUTO-RENEWAL
This Agreement shall automatically renew for successive one-year renewal terms
unless terminated by either party at least 60 days prior to the renewal date.

9. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.

10. DISPUTE RESOLUTION
Any dispute arising under this Agreement shall be resolved by binding arbitration
in the courts of Delaware.
"""


@pytest.fixture
def sample_contract_text() -> str:
    return SAMPLE_CONTRACT


@pytest.fixture
def sample_contract_bytes() -> bytes:
    # Plain-text bytes; the parser's text fallback handles this in offline tests.
    return SAMPLE_CONTRACT.encode("utf-8")
