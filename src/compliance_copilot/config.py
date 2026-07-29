"""Centralized configuration for UAE Compliance Copilot.

All runtime behavior is controlled via environment variables (optionally loaded
from a `.env` file). No secrets or model names are hardcoded anywhere else in
the codebase — every agent resolves its LLM provider through :mod:`compliance_copilot.llm.factory`,
which reads from this module.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMRoleConfig(BaseSettings):
    """Resolved LLM configuration for a single agent role."""

    provider: str = "ollama"
    model: str = "llama3.1"
    base_url: str | None = "http://localhost:11434"
    api_key: str | None = None
    max_retries: int = 3
    timeout_seconds: int = 30


class Settings(BaseSettings):
    """Application-wide settings, populated from environment variables / `.env`.

    Role-specific overrides (``ORCHESTRATOR_LLM_*`` / ``SUBAGENT_LLM_*``) let the
    supervisor and specialist agents run on different providers/models for
    hybrid cloud+local deployments. If a role override is not set, the default
    ``LLM_*`` values are used for that role.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Default LLM configuration (applies to any role without a specific override)
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    llm_model: str = Field(default="llama3.1", alias="LLM_MODEL")
    llm_base_url: str | None = Field(default="http://localhost:11434", alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    llm_timeout_seconds: int = Field(default=30, alias="LLM_TIMEOUT_SECONDS")

    # Orchestrator (supervisor) role overrides
    orchestrator_llm_provider: str | None = Field(default=None, alias="ORCHESTRATOR_LLM_PROVIDER")
    orchestrator_llm_model: str | None = Field(default=None, alias="ORCHESTRATOR_LLM_MODEL")
    orchestrator_llm_base_url: str | None = Field(default=None, alias="ORCHESTRATOR_LLM_BASE_URL")
    orchestrator_llm_api_key: str | None = Field(default=None, alias="ORCHESTRATOR_LLM_API_KEY")

    # Sub-agent role overrides
    subagent_llm_provider: str | None = Field(default=None, alias="SUBAGENT_LLM_PROVIDER")
    subagent_llm_model: str | None = Field(default=None, alias="SUBAGENT_LLM_MODEL")
    subagent_llm_base_url: str | None = Field(default=None, alias="SUBAGENT_LLM_BASE_URL")
    subagent_llm_api_key: str | None = Field(default=None, alias="SUBAGENT_LLM_API_KEY")

    # Runtime behavior
    max_tokens_per_run: int = Field(default=0, alias="MAX_TOKENS_PER_RUN")
    sanctions_match_threshold: int = Field(default=85, alias="SANCTIONS_MATCH_THRESHOLD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    def role_config(self, role: str) -> LLMRoleConfig:
        """Resolve the effective LLM config for a given agent role.

        Args:
            role: One of ``"orchestrator"``, ``"subagent"``, or any other string
                (falls back to the default configuration).

        Returns:
            The resolved :class:`LLMRoleConfig` for that role.
        """
        if role == "orchestrator" and self.orchestrator_llm_provider:
            return LLMRoleConfig(
                provider=self.orchestrator_llm_provider,
                model=self.orchestrator_llm_model or self.llm_model,
                base_url=self.orchestrator_llm_base_url or self.llm_base_url,
                api_key=self.orchestrator_llm_api_key or self.llm_api_key,
                max_retries=self.llm_max_retries,
                timeout_seconds=self.llm_timeout_seconds,
            )
        if role == "subagent" and self.subagent_llm_provider:
            return LLMRoleConfig(
                provider=self.subagent_llm_provider,
                model=self.subagent_llm_model or self.llm_model,
                base_url=self.subagent_llm_base_url or self.llm_base_url,
                api_key=self.subagent_llm_api_key or self.llm_api_key,
                max_retries=self.llm_max_retries,
                timeout_seconds=self.llm_timeout_seconds,
            )
        return LLMRoleConfig(
            provider=self.llm_provider,
            model=self.llm_model,
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            max_retries=self.llm_max_retries,
            timeout_seconds=self.llm_timeout_seconds,
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide :class:`Settings` instance."""
    return Settings()
