"""Ollama provider — local model serving via the Ollama HTTP API.

Ollama's `/api/chat` endpoint is not OpenAI-wire-compatible, so this is a
dedicated implementation rather than reusing `OpenAICompatibleProvider`.
"""

from __future__ import annotations

import httpx

from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    name = "ollama"
    default_base_url = "http://localhost:11434"

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(model, **kwargs)
        if not self.base_url:
            self.base_url = self.default_base_url

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = self.base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"ollama request timed out: {exc}", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code >= 500
            raise LLMError(
                f"ollama returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                provider=self.name,
                retryable=retryable,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                f"ollama request failed (is the server running at {self.base_url}?): {exc}",
                provider=self.name,
                retryable=True,
            ) from exc

        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(
                f"ollama returned a malformed response: {data!r}",
                provider=self.name,
                retryable=False,
            ) from exc

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )
