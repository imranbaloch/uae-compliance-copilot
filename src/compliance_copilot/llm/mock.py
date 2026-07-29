"""Deterministic mock provider used throughout the test suite.

Using a real LLM in tests would make them slow, flaky, and dependent on
network access / API keys. `MockProvider` implements the same `LLMProvider`
interface but returns scripted or deterministic responses, so the rest of the
system (agents, graph engine, config switching) can be tested in full without
any external dependency.
"""

from __future__ import annotations

from collections.abc import Callable

from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """Test double for :class:`LLMProvider`.

    Args:
        model: Arbitrary model name label.
        script: Optional list of canned response strings, returned in order
            (one per call; the last one repeats once exhausted). If omitted,
            `responder` is used instead.
        responder: Optional callable ``(messages) -> str`` for dynamic
            responses based on the input, useful for simulating an agent that
            reasons about its input.
        fail_times: Number of calls that should raise a retryable
            :class:`LLMError` before succeeding, to test retry logic.
    """

    name = "mock"

    def __init__(
        self,
        model: str = "mock-model",
        *,
        script: list[str] | None = None,
        responder: Callable[[list[LLMMessage]], str] | None = None,
        fail_times: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(model, **kwargs)
        self.script = script or []
        self.responder = responder
        self.fail_times = fail_times
        self._call_count = 0
        self.calls: list[list[LLMMessage]] = []

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.calls.append(messages)
        self._call_count += 1

        if self._call_count <= self.fail_times:
            raise LLMError("simulated transient failure", provider=self.name, retryable=True)

        if self.responder is not None:
            content = self.responder(messages)
        elif self.script:
            idx = min(self._call_count - 1, len(self.script) - 1)
            content = self.script[idx]
        else:
            content = "OK"

        prompt_tokens = sum(len(m.content.split()) for m in messages)
        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=len(content.split()),
        )
