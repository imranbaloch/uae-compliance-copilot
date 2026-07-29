from __future__ import annotations

from datetime import date
from decimal import Decimal

from compliance_copilot.memory.state import Invoice
from compliance_copilot.tools.tax_rules import validate_invoice, validate_invoices


def _invoice(**overrides) -> Invoice:
    defaults = dict(
        invoice_id="INV-1",
        issue_date=date(2026, 7, 1),
        seller_trn="100234567800003",
        amount=Decimal("1000.00"),
        vat_amount=Decimal("50.00"),
        tax_category="standard_rated",
        counterparty_name="Acme LLC",
    )
    defaults.update(overrides)
    return Invoice(**defaults)


def test_clean_invoice_has_no_findings():
    findings = validate_invoice(_invoice())
    assert findings == []


def test_missing_trn_is_critical():
    findings = validate_invoice(_invoice(seller_trn=None))
    codes = [f.code for f in findings]
    assert "MISSING_SELLER_TRN" in codes
    assert next(f for f in findings if f.code == "MISSING_SELLER_TRN").severity == "critical"


def test_vat_mismatch_flagged():
    findings = validate_invoice(_invoice(vat_amount=Decimal("0.00")))
    codes = [f.code for f in findings]
    assert "VAT_AMOUNT_MISMATCH" in codes


def test_zero_rated_with_vat_is_flagged():
    findings = validate_invoice(_invoice(tax_category="zero_rated", vat_amount=Decimal("50.00")))
    codes = [f.code for f in findings]
    assert "VAT_ON_ZERO_RATED" in codes


def test_zero_rated_without_vat_is_clean():
    findings = validate_invoice(_invoice(tax_category="zero_rated", vat_amount=Decimal("0.00")))
    assert findings == []


def test_non_positive_amount_flagged():
    findings = validate_invoice(_invoice(amount=Decimal("0.00")))
    codes = [f.code for f in findings]
    assert "NON_POSITIVE_AMOUNT" in codes


def test_missing_counterparty_flagged():
    findings = validate_invoice(_invoice(counterparty_name=None))
    codes = [f.code for f in findings]
    assert "MISSING_COUNTERPARTY_NAME" in codes


def test_validate_invoices_aggregates_across_batch():
    invoices = [_invoice(invoice_id="A"), _invoice(invoice_id="B", seller_trn=None)]
    findings = validate_invoices(invoices)
    assert len(findings) == 1
    assert findings[0].invoice_id == "B"
