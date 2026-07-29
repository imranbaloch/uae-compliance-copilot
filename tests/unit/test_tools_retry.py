from __future__ import annotations

import pytest

from compliance_copilot.llm.base import LLMError
from compliance_copilot.tools.retry import with_retry


def test_with_retry_succeeds_after_transient_failures():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise LLMError("transient", provider="test", retryable=True)
        return "ok"

    result = with_retry(flaky, max_attempts=5)
    assert result == "ok"
    assert attempts["count"] == 3


def test_with_retry_raises_after_exhausting_attempts():
    def always_fails():
        raise LLMError("still broken", provider="test", retryable=True)

    with pytest.raises(LLMError):
        with_retry(always_fails, max_attempts=3)


def test_with_retry_does_not_retry_non_retryable_errors():
    calls = {"count": 0}

    def fails_permanently():
        calls["count"] += 1
        raise LLMError("bad api key", provider="test", retryable=False)

    with pytest.raises(LLMError):
        with_retry(fails_permanently, max_attempts=5)
    assert calls["count"] == 1
