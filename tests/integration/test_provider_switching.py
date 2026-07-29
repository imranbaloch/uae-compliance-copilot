"""Verify that switching LLM_PROVIDER (and role overrides) is purely a
configuration change with no code changes required, and that hybrid
(different provider per role) configuration resolves correctly end-to-end."""

from __future__ import annotations

from compliance_copilot.config import Settings
from compliance_copilot.llm.factory import get_llm_provider
from compliance_copilot.llm.providers.groq_provider import GroqProvider
from compliance_copilot.llm.providers.ollama_provider import OllamaProvider


def test_switching_default_provider_via_settings():
    ollama_settings = Settings(LLM_PROVIDER="ollama", LLM_MODEL="llama3.1")
    groq_settings = Settings(LLM_PROVIDER="groq", LLM_MODEL="llama-3.1-70b", LLM_API_KEY="gsk-x")

    ollama_provider = get_llm_provider("default", settings=ollama_settings)
    groq_provider = get_llm_provider("default", settings=groq_settings)

    assert isinstance(ollama_provider, OllamaProvider)
    assert isinstance(groq_provider, GroqProvider)


def test_hybrid_orchestrator_and_subagent_use_different_providers():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1",
        ORCHESTRATOR_LLM_PROVIDER="groq",
        ORCHESTRATOR_LLM_MODEL="llama-3.1-70b",
        ORCHESTRATOR_LLM_API_KEY="gsk-x",
    )

    orchestrator_provider = get_llm_provider("orchestrator", settings=settings)
    subagent_provider = get_llm_provider("subagent", settings=settings)

    assert isinstance(orchestrator_provider, GroqProvider)
    assert isinstance(subagent_provider, OllamaProvider)  # falls back to default
