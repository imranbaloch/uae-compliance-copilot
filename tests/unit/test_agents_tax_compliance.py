from __future__ import annotations

from datetime import date
from decimal import Decimal

from compliance_copilot.agents.tax_compliance import TaxComplianceAgent
from compliance_copilot.llm.base import LLMError
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState, Invoice


def test_tax_compliance_runs_deterministic_rules():
    agent = TaxComplianceAgent(llm_provider=MockProvider())
    invoice = Invoice(
        invoice_id="INV-1",
        issue_date=date(2026, 7, 1),
        seller_trn=None,
        amount=Decimal("100"),
        vat_amount=Decimal("0"),
    )
    state = ComplianceState(invoices=[invoice])

    result = agent.run(state)

    assert any(f.code == "MISSING_SELLER_TRN" for f in result.tax_findings)


def test_tax_compliance_uses_llm_for_ambiguous_category():
    agent = TaxComplianceAgent(llm_provider=MockProvider(script=["zero_rated"]))
    invoice = Invoice(
        invoice_id="INV-2",
        issue_date=date(2026, 7, 1),
        seller_trn="100234567800003",
        amount=Decimal("100"),
        vat_amount=Decimal("0"),
        tax_category=None,
        raw={"description": "Export of goods to Saudi Arabia"},
    )
    state = ComplianceState(invoices=[invoice])

    result = agent.run(state)

    suggestion = [f for f in result.tax_findings if f.code == "LLM_SUGGESTED_CLASSIFICATION"]
    assert len(suggestion) == 1
    assert "zero_rated" in suggestion[0].message


def test_tax_compliance_skips_llm_when_no_description():
    agent = TaxComplianceAgent(llm_provider=MockProvider(script=["zero_rated"]))
    invoice = Invoice(
        invoice_id="INV-3",
        issue_date=date(2026, 7, 1),
        seller_trn="100234567800003",
        amount=Decimal("100"),
        vat_amount=Decimal("5"),
        tax_category=None,
    )
    state = ComplianceState(invoices=[invoice])

    result = agent.run(state)

    assert not any(f.code == "LLM_SUGGESTED_CLASSIFICATION" for f in result.tax_findings)


def test_tax_compliance_llm_failure_degrades_gracefully():
    class BoomProvider(MockProvider):
        def generate(self, *args, **kwargs):
            raise LLMError("provider down", provider="mock", retryable=False)

    agent = TaxComplianceAgent(llm_provider=BoomProvider())
    invoice = Invoice(
        invoice_id="INV-4",
        issue_date=date(2026, 7, 1),
        seller_trn="100234567800003",
        amount=Decimal("100"),
        vat_amount=Decimal("5"),
        tax_category=None,
        raw={"description": "some ambiguous service"},
    )
    state = ComplianceState(invoices=[invoice])

    # Should not raise, even though the LLM call fails.
    result = agent.run(state)
    assert not any(f.code == "LLM_SUGGESTED_CLASSIFICATION" for f in result.tax_findings)
