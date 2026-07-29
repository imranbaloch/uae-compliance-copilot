"""Shared pytest fixtures. No network access or API keys required anywhere in
the test suite — everything routes through `MockProvider`."""

from __future__ import annotations

import copy

import pytest

from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState


@pytest.fixture
def mock_llm() -> MockProvider:
    return MockProvider(script=["OK"])


SAMPLE_RAW_INPUT = {
    "invoices": [
        {
            "invoice_id": "INV-1",
            "issue_date": "2026-07-05",
            "seller_trn": "100234567800003",
            "amount": "1000.00",
            "vat_amount": "50.00",
            "tax_category": "standard_rated",
            "counterparty_name": "Al Farooq Trading FZE",
        },
        {
            "invoice_id": "INV-2",
            "issue_date": "2026-07-06",
            "seller_trn": None,
            "amount": "2000.00",
            "vat_amount": "0.00",
            "counterparty_name": "Clean Co LLC",
        },
    ],
    "transactions": [
        {
            "transaction_id": "TXN-1",
            "date": "2026-07-06",
            "amount": "5000.00",
            "direction": "credit",
            "counterparty_name": "Al Farooq Trading FZE",
        }
    ],
    "counterparties": [
        {"name": "Al Farooq Trading FZE", "country": "AE"},
        {"name": "Clean Co LLC", "country": "AE"},
    ],
}


@pytest.fixture
def sample_raw_input() -> dict:
    return copy.deepcopy(SAMPLE_RAW_INPUT)


@pytest.fixture
def empty_state() -> ComplianceState:
    return ComplianceState()
