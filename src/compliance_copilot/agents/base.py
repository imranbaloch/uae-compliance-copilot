"""Base class every agent inherits from.

Provides: LLM resolution scoped to the agent's role (orchestrator vs.
sub-agent, enabling hybrid cloud/local deployments), a `call_llm` helper with
retry logic and token-usage accounting, and a `safe_run` wrapper so a failing
agent degrades to a structured `AgentError` on shared state instead of
crashing the whole pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from compliance_copilot.config import Settings, get_settings
from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider
from compliance_copilot.llm.factory import get_llm_provider
from compliance_copilot.logging_config import get_logger
from compliance_copilot.memory.state import ComplianceState
from compliance_copilot.tools.retry import with_retry

AgentRole = Literal["orchestrator", "subagent"]


class BaseAgent(ABC):
    """Common behavior for supervisor and specialist agents.

    Args:
        role: Which LLM role config to resolve (`"orchestrator"` or
            `"subagent"`), letting hybrid deployments run the supervisor on a
            stronger cloud model and specialists on a cheaper/local one.
        settings: Optional explicit settings (defaults to process settings).
        llm_provider: Optional pre-built provider — primarily for tests, to
            inject a `MockProvider` without touching environment variables.
    """

    name: str = "base_agent"
    role: AgentRole = "subagent"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._llm_provider = llm_provider
        self.log = get_logger(self.name)

    @property
    def llm(self) -> LLMProvider:
        """Lazily resolve the LLM provider for this agent's role."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider(self.role, settings=self.settings)
        return self._llm_provider

    def call_llm(
        self,
        state: ComplianceState,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Call the LLM with retry, accounting tokens on `state`.

        Raises:
            LLMError: If all retry attempts are exhausted or the failure is
                non-retryable. Callers should catch this and fall back to a
                deterministic response where possible.
        """
        provider = self.llm

        def _call():
            return provider.generate(messages, temperature=temperature, max_tokens=max_tokens)

        response = with_retry(_call, max_attempts=provider.max_retries)
        state.token_usage += response.total_tokens
        return response.content

    @abstractmethod
    def run(self, state: ComplianceState) -> ComplianceState:
        """Do this agent's work, mutating/returning `state`.

        Implementations should catch expected per-record issues internally and
        record them as findings/errors rather than raising, but may let
        unexpected exceptions propagate — `safe_run` will catch them.
        """
        raise NotImplementedError

    def safe_run(self, state: ComplianceState) -> ComplianceState:
        """Graph-node entry point: runs `run()` and never raises.

        On failure, records a structured `AgentError` on `state` so the
        Supervisor and Report Synthesis Agent can report partial results
        instead of the whole pipeline crashing.
        """
        try:
            state = self.run(state)
            state.mark_complete(self.name)
        except LLMError as exc:
            self.log.error("agent_failed", error=str(exc), retryable=exc.retryable)
            state.record_error(self.name, str(exc), retryable=exc.retryable)
        except Exception as exc:  # noqa: BLE001 - isolate agent failures from the pipeline
            self.log.error("agent_failed", error=str(exc))
            state.record_error(self.name, str(exc), retryable=False)
        return state
