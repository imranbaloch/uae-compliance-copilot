"""Unified LLM provider interface.

Every concrete provider (OpenAI, Anthropic, Ollama, Azure OpenAI, Groq, a custom
OpenAI-compatible endpoint, or the test :class:`~compliance_copilot.llm.mock.MockProvider`)
implements :class:`LLMProvider`. Agents never talk to a vendor SDK directly —
they only depend on this interface, so swapping providers is a configuration
change, not a code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class LLMMessage(BaseModel):
    """A single chat message."""

    role: Role
    content: str


class LLMResponse(BaseModel):
    """Normalized response returned by every provider."""

    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMError(Exception):
    """Raised when a provider call fails.

    Attributes:
        provider: Name of the provider that raised the error.
        retryable: Whether retrying the same request might succeed (e.g. a
            timeout or 5xx) versus a permanent failure (e.g. bad API key).
    """

    def __init__(self, message: str, *, provider: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    name: str = "base"

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate a completion for the given messages.

        Implementations must raise :class:`LLMError` on failure rather than
        letting provider-specific exceptions escape, so callers can handle all
        providers uniformly.
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.__class__.__name__}(model={self.model!r})"


class GenerationParams(BaseModel):
    """Optional structured params agents can pass through to `generate`."""

    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
