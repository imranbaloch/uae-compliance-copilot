from __future__ import annotations

from compliance_copilot.agents.report import ReportSynthesisAgent
from compliance_copilot.llm.base import LLMError
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import AnomalyFinding, ComplianceState, TaxFinding


def test_report_agent_produces_report_with_llm_summary():
    agent = ReportSynthesisAgent(
        llm_provider=MockProvider(script=["An LLM summary.", "- Do the thing"])
    )
    state = ComplianceState(
        tax_findings=[TaxFinding(invoice_id="I1", severity="critical", code="X", message="bad")]
    )

    result = agent.run(state)

    assert result.report is not None
    assert result.report.summary == "An LLM summary."
    assert result.report.recommended_actions == ["Do the thing"]
    assert result.report.risk_score == 25


def test_report_agent_falls_back_when_llm_fails():
    class BoomProvider(MockProvider):
        def generate(self, *args, **kwargs):
            raise LLMError("down", provider="mock", retryable=False)

    agent = ReportSynthesisAgent(llm_provider=BoomProvider())
    state = ComplianceState(
        anomalies=[AnomalyFinding(record_id="A1", severity="critical", code="Y", message="oops")]
    )

    result = agent.run(state)

    assert result.report is not None
    assert "Reviewed" in result.report.summary
    assert result.report.recommended_actions  # deterministic fallback list is non-empty


def test_report_agent_zero_findings_low_risk():
    agent = ReportSynthesisAgent(llm_provider=MockProvider(script=["All clear."]))
    state = ComplianceState()

    result = agent.run(state)

    assert result.report.risk_score == 0
    assert result.report.recommended_actions == [
        "No urgent issues found — keep reconciling records regularly."
    ]
