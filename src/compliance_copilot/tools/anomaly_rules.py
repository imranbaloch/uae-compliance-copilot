"""Deterministic reconciliation anomaly detection rules."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from compliance_copilot.memory.state import AnomalyFinding, Invoice, Transaction

ROUND_NUMBER_THRESHOLD = Decimal("1000")


def detect_duplicate_invoices(invoices: list[Invoice]) -> list[AnomalyFinding]:
    """Flag invoice IDs that appear more than once (likely double-entry)."""
    counts = Counter(inv.invoice_id for inv in invoices)
    findings = []
    for invoice_id, count in counts.items():
        if count > 1:
            findings.append(
                AnomalyFinding(
                    record_id=invoice_id,
                    severity="critical",
                    code="DUPLICATE_INVOICE_ID",
                    message=f"Invoice ID '{invoice_id}' appears {count} times in the batch.",
                )
            )
    return findings


def detect_round_number_transactions(transactions: list[Transaction]) -> list[AnomalyFinding]:
    """Flag suspiciously round-number transactions above a threshold.

    Round, large-amount transactions are a common heuristic for potential
    structuring/anomalies worth a human look — not proof of wrongdoing.
    """
    findings = []
    for txn in transactions:
        if txn.amount >= ROUND_NUMBER_THRESHOLD and txn.amount % ROUND_NUMBER_THRESHOLD == 0:
            findings.append(
                AnomalyFinding(
                    record_id=txn.transaction_id,
                    severity="info",
                    code="ROUND_NUMBER_TRANSACTION",
                    message=f"Transaction {txn.transaction_id} is a round amount of "
                    f"{txn.amount} — worth a manual sanity check.",
                )
            )
    return findings


def detect_negative_or_zero_amounts(transactions: list[Transaction]) -> list[AnomalyFinding]:
    """Flag transactions with non-positive amounts (likely data entry errors)."""
    findings = []
    for txn in transactions:
        if txn.amount <= 0:
            findings.append(
                AnomalyFinding(
                    record_id=txn.transaction_id,
                    severity="warning",
                    code="NON_POSITIVE_TRANSACTION_AMOUNT",
                    message=f"Transaction {txn.transaction_id} has amount {txn.amount}, "
                    "likely a data entry error.",
                )
            )
    return findings


def detect_anomalies(
    invoices: list[Invoice], transactions: list[Transaction]
) -> list[AnomalyFinding]:
    """Run all anomaly rules and return the combined findings."""
    return [
        *detect_duplicate_invoices(invoices),
        *detect_round_number_transactions(transactions),
        *detect_negative_or_zero_amounts(transactions),
    ]
