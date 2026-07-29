"""Unit tests for concrete LLM providers, with `httpx.post` monkeypatched so
no real network calls are made."""

from __future__ import annotations

import httpx
import pytest

from compliance_copilot.llm.base import LLMError, LLMMessage
from compliance_copilot.llm.providers import openai_compatible
from compliance_copilot.llm.providers.anthropic_provider import AnthropicProvider
from compliance_copilot.llm.providers.azure_provider import AzureOpenAIProvider
from compliance_copilot.llm.providers.ollama_provider import OllamaProvider
from compliance_copilot.llm.providers.openai_provider import OpenAIProvider


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)


MSGS = [LLMMessage(role="user", content="hello")]


# --- OpenAI-compatible (openai/groq/custom share this code path) ------------


def test_openai_provider_success(monkeypatch):
    def fake_post(url, json, headers, timeout):
        assert "chat/completions" in url
        return FakeResponse(
            {
                "choices": [{"message": {"content": "hi there"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            }
        )

    monkeypatch.setattr(openai_compatible.httpx, "post", fake_post)
    provider = OpenAIProvider("gpt-4o-mini", api_key="sk-test")
    response = provider.generate(MSGS)
    assert response.content == "hi there"
    assert response.prompt_tokens == 5
    assert response.provider == "openai"


def test_openai_provider_malformed_response_raises(monkeypatch):
    monkeypatch.setattr(
        openai_compatible.httpx, "post", lambda *a, **k: FakeResponse({"unexpected": True})
    )
    provider = OpenAIProvider("gpt-4o-mini", api_key="sk-test")
    with pytest.raises(LLMError) as exc_info:
        provider.generate(MSGS)
    assert exc_info.value.retryable is False


def test_openai_provider_5xx_is_retryable(monkeypatch):
    monkeypatch.setattr(
        openai_compatible.httpx, "post", lambda *a, **k: FakeResponse({}, status_code=500)
    )
    provider = OpenAIProvider("gpt-4o-mini", api_key="sk-test")
    with pytest.raises(LLMError) as exc_info:
        provider.generate(MSGS)
    assert exc_info.value.retryable is True


def test_openai_provider_4xx_is_not_retryable(monkeypatch):
    monkeypatch.setattr(
        openai_compatible.httpx, "post", lambda *a, **k: FakeResponse({}, status_code=401)
    )
    provider = OpenAIProvider("gpt-4o-mini", api_key="sk-test")
    with pytest.raises(LLMError) as exc_info:
        provider.generate(MSGS)
    assert exc_info.value.retryable is False


def test_openai_provider_timeout_is_retryable(monkeypatch):
    def fake_post(*a, **k):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(openai_compatible.httpx, "post", fake_post)
    provider = OpenAIProvider("gpt-4o-mini", api_key="sk-test")
    with pytest.raises(LLMError) as exc_info:
        provider.generate(MSGS)
    assert exc_info.value.retryable is True


def test_custom_provider_requires_base_url():
    with pytest.raises(LLMError):
        from compliance_copilot.llm.providers.custom_provider import CustomProvider

        CustomProvider("local-model")


# --- Ollama -------------------------------------------------------------------


def test_ollama_provider_success(monkeypatch):
    import compliance_copilot.llm.providers.ollama_provider as ollama_mod

    def fake_post(url, json, timeout):
        assert url.endswith("/api/chat")
        return FakeResponse({"message": {"content": "hi"}, "prompt_eval_count": 3, "eval_count": 1})

    monkeypatch.setattr(ollama_mod.httpx, "post", fake_post)
    provider = OllamaProvider("llama3.1")
    response = provider.generate(MSGS)
    assert response.content == "hi"
    assert response.provider == "ollama"


def test_ollama_provider_connection_error_is_retryable(monkeypatch):
    import compliance_copilot.llm.providers.ollama_provider as ollama_mod

    def fake_post(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(ollama_mod.httpx, "post", fake_post)
    provider = OllamaProvider("llama3.1")
    with pytest.raises(LLMError) as exc_info:
        provider.generate(MSGS)
    assert exc_info.value.retryable is True


# --- Anthropic ------------------------------------------------------------------


def test_anthropic_requires_api_key():
    with pytest.raises(LLMError):
        AnthropicProvider("claude-sonnet-5")


def test_anthropic_provider_success(monkeypatch):
    import compliance_copilot.llm.providers.anthropic_provider as anthropic_mod

    def fake_post(url, json, headers, timeout):
        assert headers["x-api-key"] == "sk-ant-test"
        return FakeResponse(
            {
                "content": [{"text": "hello from claude"}],
                "usage": {"input_tokens": 4, "output_tokens": 3},
            }
        )

    monkeypatch.setattr(anthropic_mod.httpx, "post", fake_post)
    provider = AnthropicProvider("claude-sonnet-5", api_key="sk-ant-test")
    response = provider.generate(
        [LLMMessage(role="system", content="be nice"), LLMMessage(role="user", content="hi")]
    )
    assert response.content == "hello from claude"
    assert response.prompt_tokens == 4


# --- Azure -----------------------------------------------------------------------


def test_azure_requires_base_url_and_api_key():
    with pytest.raises(LLMError):
        AzureOpenAIProvider("gpt-4o", api_key="key-only")
    with pytest.raises(LLMError):
        AzureOpenAIProvider("gpt-4o", base_url="https://x.openai.azure.com")


def test_azure_provider_success(monkeypatch):
    import compliance_copilot.llm.providers.azure_provider as azure_mod

    def fake_post(url, json, headers, timeout):
        assert "api-version=" in url
        assert headers["api-key"] == "az-key"
        return FakeResponse(
            {
                "choices": [{"message": {"content": "azure says hi"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        )

    monkeypatch.setattr(azure_mod.httpx, "post", fake_post)
    provider = AzureOpenAIProvider(
        "gpt-4o", base_url="https://example.openai.azure.com", api_key="az-key"
    )
    response = provider.generate(MSGS)
    assert response.content == "azure says hi"
