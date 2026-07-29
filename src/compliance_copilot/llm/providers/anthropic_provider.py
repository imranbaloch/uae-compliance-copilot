"""Anthropic provider (Messages API)."""

from __future__ import annotations

import httpx

from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    default_base_url = "https://api.anthropic.com"

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(model, **kwargs)
        if not self.base_url:
            self.base_url = self.default_base_url
        if not self.api_key:
            raise LLMError(
                "anthropic requires LLM_API_KEY to be set", provider=self.name, retryable=False
            )

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        chat_messages = [m.model_dump() for m in messages if m.role != "system"]

        url = self.base_url.rstrip("/") + "/v1/messages"
        payload: dict = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"anthropic request timed out: {exc}", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code >= 500 or exc.response.status_code == 429
            raise LLMError(
                f"anthropic returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                provider=self.name,
                retryable=retryable,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                f"anthropic request failed: {exc}", provider=self.name, retryable=True
            ) from exc

        try:
            content = "".join(block.get("text", "") for block in data["content"])
            usage = data.get("usage", {})
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"anthropic returned a malformed response: {data!r}",
                provider=self.name,
                retryable=False,
            ) from exc

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )
