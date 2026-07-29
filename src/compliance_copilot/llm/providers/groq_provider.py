"""Groq provider — OpenAI-compatible wire format, hosted inference for fast/cheap open models."""

from __future__ import annotations

from compliance_copilot.llm.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
