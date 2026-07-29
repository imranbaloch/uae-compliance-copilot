"""Example: run the full pipeline with the MockProvider (no LLM/API key needed).

Useful to see the pipeline's deterministic behavior (rules-based findings,
fallback summary/actions templates) without configuring any provider at all.

Usage:
    python examples/run_with_mock.py
"""

from __future__ import annotations

import json
from pathlib import Path

from compliance_copilot.agents.anomaly import AnomalyDetectionAgent
from compliance_copilot.agents.intake import IntakeAgent
from compliance_copilot.agents.report import ReportSynthesisAgent
from compliance_copilot.agents.sanctions import SanctionsScreeningAgent
from compliance_copilot.agents.supervisor import Supervisor
from compliance_copilot.agents.tax_compliance import TaxComplianceAgent
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.logging_config import configure_logging

SAMPLE_PATH = Path(__file__).parent / "sample_data" / "sample_input.json"


def main() -> None:
    configure_logging("INFO")
    mock = MockProvider(script=["standard_rated"])

    supervisor = Supervisor(
        llm_provider=mock,
        intake=IntakeAgent(llm_provider=mock),
        tax_compliance=TaxComplianceAgent(llm_provider=mock),
        anomaly_detection=AnomalyDetectionAgent(llm_provider=mock),
        sanctions_screening=SanctionsScreeningAgent(llm_provider=mock),
        report_synthesis=ReportSynthesisAgent(llm_provider=mock),
    )

    raw_input = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    result = supervisor.run_pipeline(raw_input)
    state = result.state

    print(f"\nPlan: {state.plan}\n")
    if state.report:
        print(json.dumps(state.report.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
