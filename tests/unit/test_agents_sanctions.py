from __future__ import annotations

from compliance_copilot.agents.sanctions import SanctionsScreeningAgent
from compliance_copilot.config import Settings
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState, Counterparty


def test_sanctions_agent_finds_known_hit():
    settings = Settings(LLM_PROVIDER="mock", SANCTIONS_MATCH_THRESHOLD=85)
    agent = SanctionsScreeningAgent(settings=settings, llm_provider=MockProvider())
    state = ComplianceState(counterparties=[Counterparty(name="Al Farooq Trading FZE")])

    result = agent.run(state)

    assert len(result.sanctions_hits) == 1
    assert result.sanctions_hits[0].counterparty_name == "Al Farooq Trading FZE"


def test_sanctions_agent_clean_counterparty_no_hits():
    settings = Settings(LLM_PROVIDER="mock", SANCTIONS_MATCH_THRESHOLD=85)
    agent = SanctionsScreeningAgent(settings=settings, llm_provider=MockProvider())
    state = ComplianceState(counterparties=[Counterparty(name="Totally Clean Bakery LLC")])

    result = agent.run(state)

    assert result.sanctions_hits == []


def test_sanctions_agent_no_counterparties_no_hits():
    settings = Settings(LLM_PROVIDER="mock", SANCTIONS_MATCH_THRESHOLD=85)
    agent = SanctionsScreeningAgent(settings=settings, llm_provider=MockProvider())
    state = ComplianceState()

    result = agent.run(state)

    assert result.sanctions_hits == []
