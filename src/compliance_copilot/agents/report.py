"""Report Synthesis Agent.

Merges every specialist agent's findings into one `ComplianceReport`. The risk
score is computed deterministically (so it's reproducible and explainable);
the executive summary and recommended actions are LLM-written for
readability, with a deterministic template fallback if the LLM call fails —
so a complete, useful report is always produced even with no LLM configured.
"""

from __future__ import annotations

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.llm.base import LLMError, LLMMessage
from compliance_copilot.memory.state import ComplianceReport, ComplianceState

SEVERITY_WEIGHT = {"critical": 25, "warning": 8, "info": 1}
SANCTIONS_HIT_WEIGHT = 30

SUMMARY_SYSTEM_PROMPT = (
    "You are a compliance assistant writing a short executive summary for a UAE SME owner "
    "(not a tax expert). Given finding counts, write 2-4 plain-language sentences: what was "
    "reviewed, the overall risk level, and the single most urgent thing to fix. No jargon, "
    "no bullet points, no markdown."
)

ACTIONS_SYSTEM_PROMPT = (
    "You are a compliance assistant. Given a list of raw findings, write up to 5 short, "
    "concrete recommended actions for a UAE SME owner, one per line, each starting with '- '. "
    "Be specific and prioritize the most severe findings first. No other text."
)


def _compute_risk_score(state: ComplianceState) -> int:
    score = 0
    for finding in (*state.tax_findings, *state.anomalies):
        score += SEVERITY_WEIGHT.get(finding.severity, 0)
    score += sum(SANCTIONS_HIT_WEIGHT for hit in state.sanctions_hits if hit.requires_review)
    return min(100, score)


def _fallback_summary(state: ComplianceState, risk_score: int) -> str:
    level = "low" if risk_score < 20 else "moderate" if risk_score < 50 else "high"
    return (
        f"Reviewed {len(state.invoices)} invoices, {len(state.transactions)} transactions, and "
        f"{len(state.counterparties)} counterparties. Overall compliance risk is {level} "
        f"({risk_score}/100), based on {len(state.tax_findings)} tax findings, "
        f"{len(state.anomalies)} reconciliation anomalies, and {len(state.sanctions_hits)} "
        f"sanctions screening hits. Review the flagged items below before your next filing."
    )


def _fallback_actions(state: ComplianceState) -> list[str]:
    actions: list[str] = []
    critical_tax = [f for f in state.tax_findings if f.severity == "critical"]
    if critical_tax:
        actions.append(f"Resolve {len(critical_tax)} critical tax finding(s) before filing.")
    if state.sanctions_hits:
        actions.append(
            f"Manually review {len(state.sanctions_hits)} sanctions/PEP screening hit(s)."
        )
    critical_anomalies = [a for a in state.anomalies if a.severity == "critical"]
    if critical_anomalies:
        actions.append(
            f"Investigate {len(critical_anomalies)} critical reconciliation anomaly(ies)."
        )
    if not actions:
        actions.append("No urgent issues found — keep reconciling records regularly.")
    return actions[:5]


class ReportSynthesisAgent(BaseAgent):
    name = "report_synthesis"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        risk_score = _compute_risk_score(state)
        summary = self._generate_summary(state, risk_score)
        actions = self._generate_actions(state)

        state.report = ComplianceReport(
            risk_score=risk_score,
            summary=summary,
            tax_findings=list(state.tax_findings),
            sanctions_hits=list(state.sanctions_hits),
            anomalies=list(state.anomalies),
            recommended_actions=actions,
            errors=list(state.errors),
        )
        self.log.info("report_synthesis_complete", risk_score=risk_score)
        return state

    def _generate_summary(self, state: ComplianceState, risk_score: int) -> str:
        counts = (
            f"invoices={len(state.invoices)}, transactions={len(state.transactions)}, "
            f"counterparties={len(state.counterparties)}, tax_findings={len(state.tax_findings)} "
            f"(critical={sum(1 for f in state.tax_findings if f.severity == 'critical')}), "
            f"anomalies={len(state.anomalies)}, sanctions_hits={len(state.sanctions_hits)}, "
            f"risk_score={risk_score}"
        )
        try:
            content = self.call_llm(
                state,
                [
                    LLMMessage(role="system", content=SUMMARY_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=counts),
                ],
                temperature=0.3,
                max_tokens=200,
            )
            return content.strip() or _fallback_summary(state, risk_score)
        except LLMError as exc:
            self.log.warning("summary_fallback", error=str(exc))
            return _fallback_summary(state, risk_score)

    def _generate_actions(self, state: ComplianceState) -> list[str]:
        findings_text = "\n".join(
            [
                *(f"[{f.severity}] {f.code}: {f.message}" for f in state.tax_findings),
                *(f"[{a.severity}] {a.code}: {a.message}" for a in state.anomalies),
                *(
                    f"[sanctions] {h.counterparty_name} ~ {h.matched_name} (score={h.score})"
                    for h in state.sanctions_hits
                ),
            ]
        )
        if not findings_text.strip():
            return _fallback_actions(state)
        try:
            content = self.call_llm(
                state,
                [
                    LLMMessage(role="system", content=ACTIONS_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=findings_text),
                ],
                temperature=0.3,
                max_tokens=300,
            )
            actions = [line.lstrip("- ").strip() for line in content.splitlines() if line.strip()]
            return actions[:5] if actions else _fallback_actions(state)
        except LLMError as exc:
            self.log.warning("actions_fallback", error=str(exc))
            return _fallback_actions(state)
