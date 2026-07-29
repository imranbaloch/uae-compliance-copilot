"""OpenAI provider (chat completions API)."""

from __future__ import annotations

from compliance_copilot.llm.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"
