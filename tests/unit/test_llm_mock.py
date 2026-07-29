from __future__ import annotations

import pytest

from compliance_copilot.llm.base import LLMError, LLMMessage
from compliance_copilot.llm.mock import MockProvider


def test_mock_returns_scripted_responses_in_order():
    provider = MockProvider(script=["first", "second"])
    msgs = [LLMMessage(role="user", content="hi")]

    r1 = provider.generate(msgs)
    r2 = provider.generate(msgs)
    r3 = provider.generate(msgs)  # exhausted script repeats last

    assert r1.content == "first"
    assert r2.content == "second"
    assert r3.content == "second"
    assert r1.provider == "mock"


def test_mock_default_response_is_ok():
    provider = MockProvider()
    response = provider.generate([LLMMessage(role="user", content="hi")])
    assert response.content == "OK"


def test_mock_responder_is_dynamic():
    provider = MockProvider(responder=lambda msgs: f"echo:{msgs[-1].content}")
    response = provider.generate([LLMMessage(role="user", content="hello")])
    assert response.content == "echo:hello"


def test_mock_fail_times_raises_then_succeeds():
    provider = MockProvider(script=["ok"], fail_times=2)
    msgs = [LLMMessage(role="user", content="hi")]

    with pytest.raises(LLMError) as exc_info:
        provider.generate(msgs)
    assert exc_info.value.retryable is True

    with pytest.raises(LLMError):
        provider.generate(msgs)

    response = provider.generate(msgs)
    assert response.content == "ok"


def test_mock_records_calls():
    provider = MockProvider()
    msgs = [LLMMessage(role="user", content="hi")]
    provider.generate(msgs)
    assert len(provider.calls) == 1
    assert provider.calls[0] == msgs


def test_mock_token_counts_are_word_counts():
    provider = MockProvider(script=["two words"])
    response = provider.generate([LLMMessage(role="user", content="one two three")])
    assert response.prompt_tokens == 3
    assert response.completion_tokens == 2
    assert response.total_tokens == 5
