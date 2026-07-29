from __future__ import annotations

from compliance_copilot.config import Settings


def test_default_role_config_matches_base_llm_settings():
    settings = Settings(LLM_PROVIDER="ollama", LLM_MODEL="llama3.1", LLM_BASE_URL="http://x:1")
    cfg = settings.role_config("default")
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.1"
    assert cfg.base_url == "http://x:1"


def test_orchestrator_role_config_override():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1",
        ORCHESTRATOR_LLM_PROVIDER="anthropic",
        ORCHESTRATOR_LLM_MODEL="claude-sonnet-5",
        ORCHESTRATOR_LLM_API_KEY="sk-ant-x",
    )
    cfg = settings.role_config("orchestrator")
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-sonnet-5"
    assert cfg.api_key == "sk-ant-x"


def test_subagent_role_config_falls_back_to_default_model_when_unset():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1",
        SUBAGENT_LLM_PROVIDER="ollama",
    )
    cfg = settings.role_config("subagent")
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.1"  # inherited default since SUBAGENT_LLM_MODEL unset


def test_unknown_role_falls_back_to_default():
    settings = Settings(LLM_PROVIDER="mock", LLM_MODEL="m")
    cfg = settings.role_config("some_other_role")
    assert cfg.provider == "mock"
