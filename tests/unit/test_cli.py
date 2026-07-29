from __future__ import annotations

import json

import pytest

from compliance_copilot import cli
from compliance_copilot.config import get_settings


@pytest.fixture(autouse=True)
def _mock_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-model")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_cli_requires_input_path(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["compliance-copilot"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
    assert "Usage" in capsys.readouterr().err


def test_cli_runs_pipeline_and_prints_report(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps(
            {
                "invoices": [
                    {
                        "invoice_id": "INV-1",
                        "issue_date": "2026-07-01",
                        "amount": "100",
                        "vat_amount": "5",
                        "tax_category": "standard_rated",
                    }
                ]
            }
        )
    )
    monkeypatch.setattr("sys.argv", ["compliance-copilot", str(input_path)])

    cli.main()

    out = capsys.readouterr().out
    assert "risk_score" in out
    assert "Plan:" in out
