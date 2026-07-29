"""Intake Agent — normalizes heterogeneous raw input into typed records.

Purely deterministic (no LLM call): parsing structured JSON/dict input into
Pydantic models does not benefit from an LLM and keeping it deterministic
means intake failures are always precise and reproducible. Per-record parse
errors are recorded as `AgentError`s and skipped rather than aborting the
whole batch.
"""

from __future__ import annotations

from pydantic import ValidationError

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.memory.state import ComplianceState, Counterparty, Invoice, Transaction


class IntakeAgent(BaseAgent):
    name = "intake"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        raw = state.raw_input or {}

        for i, raw_invoice in enumerate(raw.get("invoices", [])):
            try:
                state.invoices.append(Invoice(**raw_invoice))
            except ValidationError as exc:
                state.record_error(
                    self.name, f"invoice[{i}] failed validation: {exc.errors()[0]['msg']}"
                )

        for i, raw_txn in enumerate(raw.get("transactions", [])):
            try:
                state.transactions.append(Transaction(**raw_txn))
            except ValidationError as exc:
                state.record_error(
                    self.name, f"transaction[{i}] failed validation: {exc.errors()[0]['msg']}"
                )

        for i, raw_cp in enumerate(raw.get("counterparties", [])):
            try:
                state.counterparties.append(Counterparty(**raw_cp))
            except ValidationError as exc:
                state.record_error(
                    self.name, f"counterparty[{i}] failed validation: {exc.errors()[0]['msg']}"
                )

        # Also pick up counterparty names mentioned only on invoices/transactions
        # so sanctions screening covers them even if not listed explicitly.
        known = {cp.name for cp in state.counterparties}
        for source in (state.invoices, state.transactions):
            for record in source:
                cp_name = getattr(record, "counterparty_name", None)
                if cp_name and cp_name not in known:
                    state.counterparties.append(Counterparty(name=cp_name))
                    known.add(cp_name)

        self.log.info(
            "intake_complete",
            invoices=len(state.invoices),
            transactions=len(state.transactions),
            counterparties=len(state.counterparties),
            errors=len(state.errors),
        )
        return state
