from __future__ import annotations

from datetime import date
from decimal import Decimal

from compliance_copilot.memory.state import Invoice, Transaction
from compliance_copilot.tools.anomaly_rules import (
    detect_anomalies,
    detect_duplicate_invoices,
    detect_negative_or_zero_amounts,
    detect_round_number_transactions,
)


def _invoice(invoice_id: str) -> Invoice:
    return Invoice(invoice_id=invoice_id, issue_date=date(2026, 7, 1), amount=Decimal("100"))


def _txn(txn_id: str, amount: str, direction: str = "credit") -> Transaction:
    return Transaction(
        transaction_id=txn_id, date=date(2026, 7, 1), amount=Decimal(amount), direction=direction
    )


def test_detect_duplicate_invoices():
    findings = detect_duplicate_invoices([_invoice("A"), _invoice("A"), _invoice("B")])
    assert len(findings) == 1
    assert findings[0].record_id == "A"
    assert findings[0].severity == "critical"


def test_no_duplicates_no_findings():
    assert detect_duplicate_invoices([_invoice("A"), _invoice("B")]) == []


def test_detect_round_number_transactions():
    findings = detect_round_number_transactions([_txn("T1", "1000"), _txn("T2", "1234.56")])
    assert len(findings) == 1
    assert findings[0].record_id == "T1"


def test_detect_negative_or_zero_amounts():
    findings = detect_negative_or_zero_amounts([_txn("T1", "0"), _txn("T2", "100")])
    assert len(findings) == 1
    assert findings[0].record_id == "T1"


def test_detect_anomalies_combines_all_rules():
    invoices = [_invoice("A"), _invoice("A")]
    transactions = [_txn("T1", "1000"), _txn("T2", "0")]
    findings = detect_anomalies(invoices, transactions)
    codes = {f.code for f in findings}
    assert codes == {
        "DUPLICATE_INVOICE_ID",
        "ROUND_NUMBER_TRANSACTION",
        "NON_POSITIVE_TRANSACTION_AMOUNT",
    }
