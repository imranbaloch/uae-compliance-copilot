from __future__ import annotations

from datetime import date
from decimal import Decimal

from compliance_copilot.agents.anomaly import AnomalyDetectionAgent
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState, Invoice


def test_anomaly_agent_detects_duplicates():
    agent = AnomalyDetectionAgent(llm_provider=MockProvider())
    inv = Invoice(invoice_id="X", issue_date=date(2026, 7, 1), amount=Decimal("10"))
    state = ComplianceState(invoices=[inv, inv])

    result = agent.run(state)

    assert any(a.code == "DUPLICATE_INVOICE_ID" for a in result.anomalies)


def test_anomaly_agent_empty_input_no_findings():
    agent = AnomalyDetectionAgent(llm_provider=MockProvider())
    state = ComplianceState()
    result = agent.run(state)
    assert result.anomalies == []
