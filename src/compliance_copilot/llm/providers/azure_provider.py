"""Azure OpenAI provider.

Azure's chat completions endpoint uses a deployment-scoped URL and an
`api-key` header instead of `Authorization: Bearer`, so it needs its own thin
implementation on top of the OpenAI-compatible request/response shape.

`base_url` must be the full Azure resource endpoint, e.g.
``https://<resource>.openai.azure.com``. The deployment name is taken from
`model` (Azure deployments are typically named after the underlying model).
"""

from __future__ import annotations

import httpx

from compliance_copilot.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse

DEFAULT_API_VERSION = "2024-06-01"


class AzureOpenAIProvider(LLMProvider):
    name = "azure"

    def __init__(self, model: str, *, api_version: str = DEFAULT_API_VERSION, **kwargs) -> None:
        super().__init__(model, **kwargs)
        self.api_version = api_version
        if not self.base_url:
            raise LLMError(
                "azure requires LLM_BASE_URL set to your Azure resource endpoint",
                provider=self.name,
                retryable=False,
            )
        if not self.api_key:
            raise LLMError(
                "azure requires LLM_API_KEY to be set", provider=self.name, retryable=False
            )

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        url = (
            f"{self.base_url.rstrip('/')}/openai/deployments/{self.model}/chat/completions"
            f"?api-version={self.api_version}"
        )
        payload = {
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"azure request timed out: {exc}", provider=self.name, retryable=True
            ) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code >= 500 or exc.response.status_code == 429
            raise LLMError(
                f"azure returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                provider=self.name,
                retryable=retryable,
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                f"azure request failed: {exc}", provider=self.name, retryable=True
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"azure returned a malformed response: {data!r}",
                provider=self.name,
                retryable=False,
            ) from exc

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )
