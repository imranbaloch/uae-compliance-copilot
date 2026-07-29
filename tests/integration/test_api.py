"""Integration tests for the FastAPI layer (api/), using TestClient with the
Supervisor dependency overridden to use MockProvider -- no network access or
API keys required, same as the rest of the suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient wired to a Supervisor backed by MockProvider, with its
    own throwaway SQLite DB per test."""
    monkeypatch.setenv("API_DB_PATH", str(tmp_path / "test.db"))

    # Reload api.store so it picks up the patched API_DB_PATH module-level default.
    import importlib

    from api import store as store_module

    importlib.reload(store_module)

    from fastapi.testclient import TestClient

    import api.routes as routes_module
    import api.web as web_module
    from api.app import app
    from api.deps import get_supervisor
    from compliance_copilot.agents.anomaly import AnomalyDetectionAgent
    from compliance_copilot.agents.intake import IntakeAgent
    from compliance_copilot.agents.report import ReportSynthesisAgent
    from compliance_copilot.agents.sanctions import SanctionsScreeningAgent
    from compliance_copilot.agents.supervisor import Supervisor
    from compliance_copilot.agents.tax_compliance import TaxComplianceAgent
    from compliance_copilot.llm.mock import MockProvider

    def _mock_supervisor() -> Supervisor:
        mock = MockProvider(script=["standard_rated", "A concise summary.", "- Do the thing"])
        return Supervisor(
            llm_provider=mock,
            intake=IntakeAgent(llm_provider=mock),
            tax_compliance=TaxComplianceAgent(llm_provider=mock),
            anomaly_detection=AnomalyDetectionAgent(llm_provider=mock),
            sanctions_screening=SanctionsScreeningAgent(llm_provider=mock),
            report_synthesis=ReportSynthesisAgent(llm_provider=mock),
        )

    # Route modules imported `store` before the reload picked up the new path,
    # so also point them at the reloaded module directly.
    routes_module.store = store_module
    web_module.store = store_module

    app.dependency_overrides[get_supervisor] = _mock_supervisor
    store_module.init_db()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


SAMPLE_PAYLOAD = {
    "invoices": [
        {
            "invoice_id": "INV-1",
            "issue_date": "2026-07-01",
            "seller_trn": None,
            "amount": "1000.00",
            "vat_amount": "0.00",
            "counterparty_name": "Al Farooq Trading FZE",
        }
    ],
    "transactions": [],
    "counterparties": [{"name": "Al Farooq Trading FZE", "country": "AE"}],
}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root_redirects_to_web(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/web"


def test_create_report_via_json_api(client):
    resp = client.post("/api/reports", json=SAMPLE_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["report"]["risk_score"] >= 0
    assert any(f["code"] == "MISSING_SELLER_TRN" for f in body["report"]["tax_findings"])


def test_get_report_by_id(client):
    created = client.post("/api/reports", json=SAMPLE_PAYLOAD).json()
    resp = client.get(f"/api/reports/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_report_404(client):
    resp = client.get("/api/reports/does-not-exist")
    assert resp.status_code == 404


def test_list_reports(client):
    client.post("/api/reports", json=SAMPLE_PAYLOAD)
    client.post("/api/reports", json=SAMPLE_PAYLOAD)
    resp = client.get("/api/reports")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_upload_report_json_file(client):
    import json

    files = {"file": ("input.json", json.dumps(SAMPLE_PAYLOAD), "application/json")}
    resp = client.post("/api/reports/upload", files=files)
    assert resp.status_code == 200
    assert resp.json()["report"]["risk_score"] >= 0


def test_upload_report_rejects_bad_json(client):
    files = {"file": ("input.json", "not json", "application/json")}
    resp = client.post("/api/reports/upload", files=files)
    assert resp.status_code == 400


def test_web_index_renders(client):
    resp = client.get("/web/")
    assert resp.status_code == 200
    assert "Run a compliance review" in resp.text


def test_web_submit_sample_redirects_to_report(client):
    resp = client.post("/web/reports/sample", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/web/reports/")


def test_web_view_report(client):
    created = client.post("/api/reports", json=SAMPLE_PAYLOAD).json()
    resp = client.get(f"/web/reports/{created['id']}")
    assert resp.status_code == 200
    assert "risk-badge" in resp.text


def test_web_view_missing_report_returns_404_page(client):
    resp = client.get("/web/reports/does-not-exist")
    assert resp.status_code == 404
