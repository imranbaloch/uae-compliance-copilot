"""Shared state model threaded through the agent graph.

`ComplianceState` is the single source of truth passed between agents. Each
agent reads only the fields it needs and returns a partial update that is
merged back in by the graph engine — this keeps per-agent context small and
predictable instead of re-sending the full conversation/history to everyone.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

# --- Input records -----------------------------------------------------------


class Invoice(BaseModel):
    """A normalized invoice/tax-invoice record."""

    invoice_id: str
    issue_date: date
    seller_trn: str | None = None
    buyer_trn: str | None = None
    amount: Decimal
    vat_amount: Decimal = Decimal("0")
    currency: str = "AED"
    tax_category: str | None = None  # e.g. "standard_rated", "zero_rated", "exempt"
    counterparty_name: str | None = None
    raw: dict = Field(default_factory=dict)


class Transaction(BaseModel):
    """A normalized bank/ledger transaction record."""

    transaction_id: str
    date: date
    amount: Decimal
    direction: Literal["debit", "credit"]
    counterparty_name: str | None = None
    memo: str | None = None
    raw: dict = Field(default_factory=dict)


class Counterparty(BaseModel):
    """A normalized customer/supplier/counterparty record for screening."""

    name: str
    country: str | None = None
    entity_type: Literal["individual", "organization"] = "organization"
    raw: dict = Field(default_factory=dict)


# --- Agent outputs -------------------------------------------------------------


class AgentError(BaseModel):
    """Structured error report from a failed agent step (non-fatal to the run)."""

    agent: str
    message: str
    retryable: bool = False


class SanctionsHit(BaseModel):
    """A fuzzy-match hit against the sanctions/PEP list."""

    counterparty_name: str
    matched_name: str
    list_source: str
    score: float
    requires_review: bool = True


class TaxFinding(BaseModel):
    """A finding from VAT/Corporate Tax/e-invoicing validation of one invoice."""

    invoice_id: str
    severity: Literal["info", "warning", "critical"]
    code: str
    message: str


class AnomalyFinding(BaseModel):
    """A finding from reconciliation anomaly detection."""

    record_id: str
    severity: Literal["info", "warning", "critical"]
    code: str
    message: str


class ComplianceReport(BaseModel):
    """Final synthesized output of a pipeline run."""

    risk_score: int = Field(ge=0, le=100)
    summary: str
    tax_findings: list[TaxFinding] = Field(default_factory=list)
    sanctions_hits: list[SanctionsHit] = Field(default_factory=list)
    anomalies: list[AnomalyFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)


# --- Shared pipeline state ------------------------------------------------------


class ComplianceState(BaseModel):
    """The object threaded through every node of the agent graph."""

    # Raw input exactly as supplied by the caller (list-of-dict per record type).
    # The Intake Agent parses this into the typed lists below; callers may also
    # populate the typed lists directly to skip intake parsing.
    raw_input: dict = Field(default_factory=dict)

    # Supervisor's plan for this run (set before delegation begins)
    plan: str | None = None

    # Normalized/typed records
    invoices: list[Invoice] = Field(default_factory=list)
    transactions: list[Transaction] = Field(default_factory=list)
    counterparties: list[Counterparty] = Field(default_factory=list)

    # Intermediate / specialist agent outputs
    tax_findings: list[TaxFinding] = Field(default_factory=list)
    sanctions_hits: list[SanctionsHit] = Field(default_factory=list)
    anomalies: list[AnomalyFinding] = Field(default_factory=list)

    # Bookkeeping
    errors: list[AgentError] = Field(default_factory=list)
    completed_agents: list[str] = Field(default_factory=list)
    token_usage: int = 0

    # Final output, populated by the report synthesis agent
    report: ComplianceReport | None = None

    def record_error(self, agent: str, message: str, *, retryable: bool = False) -> None:
        """Append a structured error without raising, so the run can continue."""
        self.errors.append(AgentError(agent=agent, message=message, retryable=retryable))

    def mark_complete(self, agent: str) -> None:
        if agent not in self.completed_agents:
            self.completed_agents.append(agent)
