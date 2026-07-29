"""Factory that resolves the correct :class:`LLMProvider` for a given agent role.

This is the single place that maps the `LLM_PROVIDER` string (and its
`ORCHESTRATOR_*` / `SUBAGENT_*` overrides) to a concrete provider class.
Swapping providers — including switching between cloud, local, and hybrid
deployments — never requires touching agent code, only configuration.
"""

from __future__ import annotations

from compliance_copilot.config import Settings, get_settings
from compliance_copilot.llm.base import LLMError, LLMProvider
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.llm.providers.anthropic_provider import AnthropicProvider
from compliance_copilot.llm.providers.azure_provider import AzureOpenAIProvider
from compliance_copilot.llm.providers.custom_provider import CustomProvider
from compliance_copilot.llm.providers.groq_provider import GroqProvider
from compliance_copilot.llm.providers.ollama_provider import OllamaProvider
from compliance_copilot.llm.providers.openai_provider import OpenAIProvider

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "azure": AzureOpenAIProvider,
    "groq": GroqProvider,
    "custom": CustomProvider,
    "mock": MockProvider,
}


def get_llm_provider(role: str = "default", *, settings: Settings | None = None) -> LLMProvider:
    """Resolve and instantiate the configured :class:`LLMProvider` for a role.

    Args:
        role: ``"orchestrator"``, ``"subagent"``, or ``"default"``.
        settings: Optional explicit :class:`Settings` (defaults to the cached
            process-wide settings via :func:`get_settings`).

    Returns:
        A ready-to-use provider instance.

    Raises:
        LLMError: If `LLM_PROVIDER` (or its role override) names an unknown
            provider.
    """
    settings = settings or get_settings()
    role_config = settings.role_config(role)

    provider_cls = PROVIDER_REGISTRY.get(role_config.provider.lower())
    if provider_cls is None:
        known = ", ".join(sorted(PROVIDER_REGISTRY))
        raise LLMError(
            f"Unknown LLM_PROVIDER '{role_config.provider}'. Known providers: {known}",
            provider=role_config.provider,
            retryable=False,
        )

    return provider_cls(
        role_config.model,
        base_url=role_config.base_url,
        api_key=role_config.api_key,
        timeout_seconds=role_config.timeout_seconds,
        max_retries=role_config.max_retries,
    )
