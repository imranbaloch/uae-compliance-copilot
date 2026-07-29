"""Deterministic VAT / Corporate Tax / e-invoicing field validation rules.

Encodes a simplified subset of the UAE FTA's publicly documented invoice
requirements (standard VAT rate, mandatory TRN fields, zero-rated/exempt
consistency, e-invoicing readiness field presence). This is a starting point
for a compliance review, not a substitute for professional tax advice — see
README for the disclaimer.
"""

from __future__ import annotations

from decimal import Decimal

from compliance_copilot.memory.state import Invoice, TaxFinding

STANDARD_VAT_RATE = Decimal("0.05")
VAT_TOLERANCE = Decimal("0.02")  # allow small rounding differences
ZERO_RATE_CATEGORIES = {"zero_rated", "exempt", "out_of_scope"}


def validate_invoice(invoice: Invoice) -> list[TaxFinding]:
    """Run deterministic field/consistency checks against one invoice.

    Returns a list of findings (possibly empty if the invoice looks clean).
    """
    findings: list[TaxFinding] = []

    if not invoice.seller_trn:
        findings.append(
            TaxFinding(
                invoice_id=invoice.invoice_id,
                severity="critical",
                code="MISSING_SELLER_TRN",
                message="Invoice is missing the seller's Tax Registration Number (TRN), "
                "a mandatory e-invoicing field. Risk: AED 2,500 penalty per non-compliant invoice.",
            )
        )

    if invoice.amount <= 0:
        findings.append(
            TaxFinding(
                invoice_id=invoice.invoice_id,
                severity="warning",
                code="NON_POSITIVE_AMOUNT",
                message=f"Invoice amount is {invoice.amount}, which is unusual for a tax invoice.",
            )
        )

    category = (invoice.tax_category or "standard_rated").lower()
    if category in ZERO_RATE_CATEGORIES:
        if invoice.vat_amount != 0:
            findings.append(
                TaxFinding(
                    invoice_id=invoice.invoice_id,
                    severity="warning",
                    code="VAT_ON_ZERO_RATED",
                    message=f"Invoice is tagged '{category}' but has a non-zero VAT amount "
                    f"({invoice.vat_amount}). Verify classification before filing.",
                )
            )
    else:
        expected_vat = (invoice.amount * STANDARD_VAT_RATE).quantize(Decimal("0.01"))
        if abs(invoice.vat_amount - expected_vat) > (invoice.amount * VAT_TOLERANCE):
            findings.append(
                TaxFinding(
                    invoice_id=invoice.invoice_id,
                    severity="warning",
                    code="VAT_AMOUNT_MISMATCH",
                    message=f"Expected ~{expected_vat} VAT at the standard 5% rate, found "
                    f"{invoice.vat_amount}. Reconcile before filing the VAT return.",
                )
            )

    if not invoice.counterparty_name:
        findings.append(
            TaxFinding(
                invoice_id=invoice.invoice_id,
                severity="info",
                code="MISSING_COUNTERPARTY_NAME",
                message="Invoice has no counterparty name recorded, which will also block "
                "sanctions screening for this record.",
            )
        )

    return findings


def validate_invoices(invoices: list[Invoice]) -> list[TaxFinding]:
    """Validate a batch of invoices."""
    findings: list[TaxFinding] = []
    for invoice in invoices:
        findings.extend(validate_invoice(invoice))
    return findings
