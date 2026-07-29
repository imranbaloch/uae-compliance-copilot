"""Tax Compliance Agent.

Runs deterministic VAT/Corporate Tax/e-invoicing field validation
(`tools/tax_rules.py`) against every invoice, then — only for invoices left
ambiguous by the deterministic rules (missing `tax_category` but with free-text
context available) — asks the LLM to suggest a VAT treatment classification.
The LLM step is best-effort: on any failure it is skipped and the deterministic
rules' default assumption stands, so the agent degrades gracefully without an
LLM at all.
"""

from __future__ import annotations

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.llm.base import LLMError, LLMMessage
from compliance_copilot.memory.state import ComplianceState, TaxFinding
from compliance_copilot.tools.tax_rules import validate_invoices

CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a UAE VAT classification assistant. Given a short invoice description, "
    "respond with exactly one word: 'standard_rated', 'zero_rated', 'exempt', or 'unclear'. "
    "UAE VAT basics: standard rate is 5% on most goods/services; exports of goods, international "
    "transport, and some healthcare/education are typically zero-rated; certain financial services "
    "and bare land/local passenger transport are typically exempt."
)


class TaxComplianceAgent(BaseAgent):
    name = "tax_compliance"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        state.tax_findings.extend(validate_invoices(state.invoices))

        for invoice in state.invoices:
            description = invoice.raw.get("description") if invoice.raw else None
            if invoice.tax_category or not description:
                continue
            suggestion = self._classify(state, description)
            if suggestion and suggestion != "unclear":
                state.tax_findings.append(
                    TaxFinding(
                        invoice_id=invoice.invoice_id,
                        severity="info",
                        code="LLM_SUGGESTED_CLASSIFICATION",
                        message=f"No tax_category was set; based on the description, this looks "
                        f"like '{suggestion}'. Confirm with your tax advisor before filing.",
                    )
                )

        self.log.info("tax_compliance_complete", findings=len(state.tax_findings))
        return state

    def _classify(self, state: ComplianceState, description: str) -> str | None:
        """Best-effort LLM classification; returns None on any failure."""
        messages = [
            LLMMessage(role="system", content=CLASSIFICATION_SYSTEM_PROMPT),
            LLMMessage(role="user", content=description),
        ]
        try:
            content = self.call_llm(state, messages, temperature=0.0, max_tokens=16)
        except LLMError as exc:
            self.log.warning("classification_skipped", error=str(exc))
            return None
        return content.strip().lower().strip(".")
