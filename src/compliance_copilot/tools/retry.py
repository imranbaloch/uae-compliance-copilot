"""Retry helper used by agents when calling their LLM provider.

Wraps `tenacity` with the project's specific policy: retry only on
`LLMError(retryable=True)`, with exponential backoff, up to `max_attempts`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from compliance_copilot.llm.base import LLMError

T = TypeVar("T")


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, LLMError) and exc.retryable


def with_retry(fn: Callable[[], T], *, max_attempts: int = 3) -> T:
    """Call `fn` with retry-on-transient-failure semantics.

    Args:
        fn: A zero-argument callable to invoke (typically a closure around an
            `LLMProvider.generate` call).
        max_attempts: Maximum number of attempts (including the first).

    Returns:
        Whatever `fn()` returns.

    Raises:
        LLMError: Re-raised after the final attempt if all attempts fail, or
            immediately if the error is not retryable.
    """
    attempts = max(1, max_attempts)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    def _call() -> T:
        return fn()

    return _call()
