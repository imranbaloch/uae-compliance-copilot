"""Supervisor Agent — plans, delegates to specialists via the graph engine,
and exposes the synthesized result.

The Supervisor runs on the `"orchestrator"` LLM role, so a hybrid deployment
can point it at a stronger cloud model while specialists run locally. It
builds the DAG once (`intake -> {tax_compliance, anomaly_detection,
sanctions_screening} -> report_synthesis`), with sanctions screening made
conditional on there being any counterparties to screen — a real planning
decision, not just a fixed pipeline call.
"""

from __future__ import annotations

from compliance_copilot.agents.anomaly import AnomalyDetectionAgent
from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.agents.intake import IntakeAgent
from compliance_copilot.agents.report import ReportSynthesisAgent
from compliance_copilot.agents.sanctions import SanctionsScreeningAgent
from compliance_copilot.agents.tax_compliance import TaxComplianceAgent
from compliance_copilot.graph.engine import ExecutionResult, GraphEngine
from compliance_copilot.llm.base import LLMError, LLMMessage
from compliance_copilot.memory.state import ComplianceState

PLAN_SYSTEM_PROMPT = (
    "You are a compliance pipeline planner. In one sentence, describe the plan for reviewing "
    "the given number of invoices, transactions, and counterparties for UAE tax and sanctions "
    "compliance. Be concise."
)


class Supervisor(BaseAgent):
    """Orchestrator agent. Not itself a graph node — it *builds and runs* the graph."""

    name = "supervisor"
    role = "orchestrator"

    def __init__(
        self,
        *,
        intake: IntakeAgent | None = None,
        tax_compliance: TaxComplianceAgent | None = None,
        anomaly_detection: AnomalyDetectionAgent | None = None,
        sanctions_screening: SanctionsScreeningAgent | None = None,
        report_synthesis: ReportSynthesisAgent | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.intake = intake or IntakeAgent(settings=self.settings)
        self.tax_compliance = tax_compliance or TaxComplianceAgent(settings=self.settings)
        self.anomaly_detection = anomaly_detection or AnomalyDetectionAgent(settings=self.settings)
        self.sanctions_screening = sanctions_screening or SanctionsScreeningAgent(
            settings=self.settings
        )
        self.report_synthesis = report_synthesis or ReportSynthesisAgent(settings=self.settings)

    def build_graph(self) -> GraphEngine[ComplianceState]:
        """Construct the DAG. Exposed separately from `run` so tests/examples
        can inspect or extend the graph without re-implementing wiring."""
        graph: GraphEngine[ComplianceState] = GraphEngine()
        graph.add_node("intake", self.intake.safe_run)
        graph.add_node("tax_compliance", self.tax_compliance.safe_run, depends_on=["intake"])
        graph.add_node("anomaly_detection", self.anomaly_detection.safe_run, depends_on=["intake"])
        graph.add_node(
            "sanctions_screening",
            self.sanctions_screening.safe_run,
            depends_on=["intake"],
            condition=lambda s: len(s.counterparties) > 0,
        )
        graph.add_node(
            "report_synthesis",
            self.report_synthesis.safe_run,
            depends_on=["tax_compliance", "anomaly_detection", "sanctions_screening"],
        )
        return graph

    def _plan(self, state: ComplianceState) -> str:
        raw = state.raw_input or {}
        counts = (
            f"{len(raw.get('invoices', []))} invoices, {len(raw.get('transactions', []))} "
            f"transactions, {len(raw.get('counterparties', []))} counterparties"
        )
        try:
            return self.call_llm(
                state,
                [
                    LLMMessage(role="system", content=PLAN_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=counts),
                ],
                temperature=0.2,
                max_tokens=80,
            ).strip()
        except LLMError as exc:
            self.log.warning("plan_fallback", error=str(exc))
            return (
                f"Plan: normalize {counts}, run tax/e-invoicing validation, anomaly detection, and "
                "sanctions screening in parallel, then synthesize one compliance report."
            )

    def run(self, state: ComplianceState) -> ComplianceState:
        """`BaseAgent` contract — plans then delegates via `run_pipeline`'s graph."""
        state.plan = self._plan(state)
        result = self.build_graph().run(state)
        return result.state

    def run_pipeline(self, raw_input: dict) -> ExecutionResult[ComplianceState]:
        """Convenience entry point: build a fresh state from raw input, plan, and execute.

        Args:
            raw_input: Dict with optional ``"invoices"``, ``"transactions"``,
                ``"counterparties"`` keys, each a list of raw record dicts.

        Returns:
            The `ExecutionResult`, whose `.state.report` holds the final
            `ComplianceReport` (assuming `report_synthesis` ran).
        """
        state = ComplianceState(raw_input=raw_input)
        state.plan = self._plan(state)
        return self.build_graph().run(state)
