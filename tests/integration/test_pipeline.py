"""Full-graph integration tests using MockProvider end-to-end (no network)."""

from __future__ import annotations

from compliance_copilot.agents.anomaly import AnomalyDetectionAgent
from compliance_copilot.agents.intake import IntakeAgent
from compliance_copilot.agents.report import ReportSynthesisAgent
from compliance_copilot.agents.sanctions import SanctionsScreeningAgent
from compliance_copilot.agents.supervisor import Supervisor
from compliance_copilot.agents.tax_compliance import TaxComplianceAgent
from compliance_copilot.llm.mock import MockProvider


def _mock_supervisor(**mock_kwargs) -> Supervisor:
    mock = MockProvider(
        script=["standard_rated", "A concise executive summary.", "- Fix things"], **mock_kwargs
    )
    return Supervisor(
        llm_provider=mock,
        intake=IntakeAgent(llm_provider=mock),
        tax_compliance=TaxComplianceAgent(llm_provider=mock),
        anomaly_detection=AnomalyDetectionAgent(llm_provider=mock),
        sanctions_screening=SanctionsScreeningAgent(llm_provider=mock),
        report_synthesis=ReportSynthesisAgent(llm_provider=mock),
    )


def test_full_pipeline_produces_report(sample_raw_input):
    supervisor = _mock_supervisor()
    result = supervisor.run_pipeline(sample_raw_input)

    assert result.state.report is not None
    assert "intake" in result.executed
    assert "report_synthesis" in result.executed
    assert result.failed == []
    assert result.state.plan


def test_full_pipeline_data_flows_agent_to_agent(sample_raw_input):
    supervisor = _mock_supervisor()
    result = supervisor.run_pipeline(sample_raw_input)
    state = result.state

    # Intake populated typed records from raw input
    assert len(state.invoices) == 2
    assert len(state.transactions) == 1
    # Tax compliance produced at least the missing-TRN finding for INV-2
    assert any(f.code == "MISSING_SELLER_TRN" for f in state.tax_findings)
    # Sanctions screening found the known sample-list entity
    assert any(h.counterparty_name == "Al Farooq Trading FZE" for h in state.sanctions_hits)
    # Report synthesis merged everything
    assert state.report.tax_findings
    assert state.report.sanctions_hits


def test_sanctions_screening_skipped_when_no_counterparties():
    supervisor = _mock_supervisor()
    result = supervisor.run_pipeline({"invoices": [], "transactions": [], "counterparties": []})

    assert "sanctions_screening" in result.skipped
    assert result.state.report is not None
    assert result.state.report.sanctions_hits == []


def test_pipeline_continues_with_partial_results_when_an_agent_raises(sample_raw_input):
    class BoomAnomalyAgent(AnomalyDetectionAgent):
        def run(self, state):
            raise RuntimeError("simulated anomaly agent crash")

    mock = MockProvider(script=["standard_rated", "summary", "- action"])
    supervisor = Supervisor(
        llm_provider=mock,
        intake=IntakeAgent(llm_provider=mock),
        tax_compliance=TaxComplianceAgent(llm_provider=mock),
        anomaly_detection=BoomAnomalyAgent(llm_provider=mock),
        sanctions_screening=SanctionsScreeningAgent(llm_provider=mock),
        report_synthesis=ReportSynthesisAgent(llm_provider=mock),
    )

    result = supervisor.run_pipeline(sample_raw_input)

    assert result.state.report is not None  # pipeline still completes
    assert any(e.agent == "anomaly_detection" for e in result.state.errors)
    assert result.state.anomalies == []  # anomaly agent's work was skipped


def test_empty_input_produces_low_risk_report():
    supervisor = _mock_supervisor()
    result = supervisor.run_pipeline({})
    assert result.state.report is not None
    assert result.state.report.risk_score == 0
