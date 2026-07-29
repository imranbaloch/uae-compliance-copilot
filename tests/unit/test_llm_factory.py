from __future__ import annotations

import pytest

from compliance_copilot.config import Settings
from compliance_copilot.llm.base import LLMError
from compliance_copilot.llm.factory import get_llm_provider
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.llm.providers.anthropic_provider import AnthropicProvider
from compliance_copilot.llm.providers.azure_provider import AzureOpenAIProvider
from compliance_copilot.llm.providers.custom_provider import CustomProvider
from compliance_copilot.llm.providers.groq_provider import GroqProvider
from compliance_copilot.llm.providers.ollama_provider import OllamaProvider
from compliance_copilot.llm.providers.openai_provider import OpenAIProvider


def _settings(**overrides) -> Settings:
    base = {"LLM_PROVIDER": "mock", "LLM_MODEL": "mock-model"}
    base.update(overrides)
    return Settings(**base)


@pytest.mark.parametrize(
    "provider_name,expected_cls,extra",
    [
        ("openai", OpenAIProvider, {"LLM_API_KEY": "sk-test"}),
        ("groq", GroqProvider, {"LLM_API_KEY": "gsk-test"}),
        ("ollama", OllamaProvider, {}),
        (
            "anthropic",
            AnthropicProvider,
            {"LLM_API_KEY": "sk-ant-test"},
        ),
        (
            "azure",
            AzureOpenAIProvider,
            {"LLM_API_KEY": "az-test", "LLM_BASE_URL": "https://example.openai.azure.com"},
        ),
        ("custom", CustomProvider, {"LLM_BASE_URL": "http://localhost:8000/v1"}),
        ("mock", MockProvider, {}),
    ],
)
def test_factory_dispatches_to_correct_provider_class(provider_name, expected_cls, extra):
    settings = _settings(LLM_PROVIDER=provider_name, **extra)
    provider = get_llm_provider("default", settings=settings)
    assert isinstance(provider, expected_cls)


def test_factory_raises_on_unknown_provider():
    settings = _settings(LLM_PROVIDER="not-a-real-provider")
    with pytest.raises(LLMError):
        get_llm_provider("default", settings=settings)


def test_factory_uses_orchestrator_override():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1",
        ORCHESTRATOR_LLM_PROVIDER="mock",
        ORCHESTRATOR_LLM_MODEL="mock-orchestrator",
    )
    provider = get_llm_provider("orchestrator", settings=settings)
    assert isinstance(provider, MockProvider)
    assert provider.model == "mock-orchestrator"


def test_factory_uses_subagent_override():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1",
        SUBAGENT_LLM_PROVIDER="mock",
        SUBAGENT_LLM_MODEL="mock-subagent",
    )
    provider = get_llm_provider("subagent", settings=settings)
    assert isinstance(provider, MockProvider)
    assert provider.model == "mock-subagent"


def test_factory_falls_back_to_default_when_no_override():
    settings = Settings(LLM_PROVIDER="mock", LLM_MODEL="mock-default")
    provider = get_llm_provider("orchestrator", settings=settings)
    assert isinstance(provider, MockProvider)
    assert provider.model == "mock-default"
