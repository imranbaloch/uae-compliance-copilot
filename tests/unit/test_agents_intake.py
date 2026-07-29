from __future__ import annotations

from compliance_copilot.agents.intake import IntakeAgent
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState


def test_intake_parses_valid_records(sample_raw_input):
    agent = IntakeAgent(llm_provider=MockProvider())
    state = ComplianceState(raw_input=sample_raw_input)

    result = agent.run(state)

    assert len(result.invoices) == 2
    assert len(result.transactions) == 1
    assert len(result.counterparties) == 2
    assert result.errors == []


def test_intake_skips_invalid_records_and_records_error():
    agent = IntakeAgent(llm_provider=MockProvider())
    state = ComplianceState(
        raw_input={
            "invoices": [{"invoice_id": "OK", "issue_date": "2026-07-01", "amount": "10"}],
            "transactions": [
                {
                    "transaction_id": "bad",
                    "date": "not-a-date",
                    "amount": "10",
                    "direction": "credit",
                }
            ],
        }
    )

    result = agent.run(state)

    assert len(result.invoices) == 1
    assert len(result.transactions) == 0
    assert len(result.errors) == 1
    assert "transaction[0]" in result.errors[0].message


def test_intake_backfills_counterparties_from_invoices_and_transactions():
    agent = IntakeAgent(llm_provider=MockProvider())
    state = ComplianceState(
        raw_input={
            "invoices": [
                {
                    "invoice_id": "INV-1",
                    "issue_date": "2026-07-01",
                    "amount": "10",
                    "counterparty_name": "New Co LLC",
                }
            ]
        }
    )

    result = agent.run(state)

    assert any(cp.name == "New Co LLC" for cp in result.counterparties)


def test_intake_empty_input_produces_empty_state():
    agent = IntakeAgent(llm_provider=MockProvider())
    state = ComplianceState()
    result = agent.run(state)
    assert result.invoices == []
    assert result.transactions == []
    assert result.counterparties == []
