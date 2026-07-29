"""Shared implementation for any provider exposing an OpenAI-compatible
`/chat/completions` endpoint (OpenAI itself, Groq, and custom local servers
such as llama.cpp / vLLM launched with an OpenAI-compatible API)."""

from __future__ import annotations

import httpx

from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    """Base class for OpenAI-wire-format chat completion providers."""

    default_base_url: str | None = None
    chat_path: str = "/chat/completions"

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(model, **kwargs)
        if not self.base_url:
            self.base_url = self.default_base_url
        if not self.base_url:
            raise LLMError(
                f"{self.name} requires LLM_BASE_URL to be set", provider=self.name, retryable=False
            )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = self.base_url.rstrip("/") + self.chat_path
        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = httpx.post(
                url, json=payload, headers=self._headers(), timeout=self.timeout_seconds
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"{self.name} request timed out: {exc}", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code >= 500 or exc.response.status_code == 429
            raise LLMError(
                f"{self.name} returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                provider=self.name,
                retryable=retryable,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                f"{self.name} request failed: {exc}", provider=self.name, retryable=True
            ) from exc

        try:
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"{self.name} returned a malformed response: {data!r}",
                provider=self.name,
                retryable=False,
            ) from exc

        return LLMResponse(
            content=choice,
            provider=self.name,
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )
