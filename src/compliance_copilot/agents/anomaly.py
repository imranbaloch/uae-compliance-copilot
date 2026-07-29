"""Anomaly Detection Agent.

Deterministic reconciliation checks (duplicate invoice IDs, round-number
transactions, non-positive amounts) via `tools/anomaly_rules.py`. No LLM call
is needed for detection itself; narrative explanation of findings is left to
the Report Synthesis Agent, which has visibility into all specialists' output
and can write one coherent summary instead of each agent narrating in
isolation (this also keeps this agent's token cost at zero).
"""

from __future__ import annotations

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.memory.state import ComplianceState
from compliance_copilot.tools.anomaly_rules import detect_anomalies


class AnomalyDetectionAgent(BaseAgent):
    name = "anomaly_detection"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        state.anomalies.extend(detect_anomalies(state.invoices, state.transactions))
        self.log.info("anomaly_detection_complete", findings=len(state.anomalies))
        return state
