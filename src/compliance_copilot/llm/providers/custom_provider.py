"""Custom OpenAI-compatible endpoint — for llama.cpp, vLLM, LM Studio, or any
other self-hosted server that speaks the OpenAI chat completions wire format.
Requires `LLM_BASE_URL` to be set explicitly (no default)."""

from __future__ import annotations

from compliance_copilot.llm.providers.openai_compatible import OpenAICompatibleProvider


class CustomProvider(OpenAICompatibleProvider):
    name = "custom"
    default_base_url = None
