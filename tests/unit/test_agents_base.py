from __future__ import annotations

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.llm.mock import MockProvider
from compliance_copilot.memory.state import ComplianceState


class _AlwaysFailsAgent(BaseAgent):
    name = "always_fails"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        raise ValueError("intentional failure")


class _AddsFlagAgent(BaseAgent):
    name = "adds_flag"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        state.plan = "done"
        return state


def test_safe_run_catches_exceptions_and_records_error():
    agent = _AlwaysFailsAgent(llm_provider=MockProvider())
    state = ComplianceState()

    result = agent.safe_run(state)

    assert result.errors
    assert result.errors[0].agent == "always_fails"
    assert "always_fails" not in result.completed_agents


def test_safe_run_marks_complete_on_success():
    agent = _AddsFlagAgent(llm_provider=MockProvider())
    state = ComplianceState()

    result = agent.safe_run(state)

    assert result.plan == "done"
    assert "adds_flag" in result.completed_agents
    assert result.errors == []


def test_call_llm_accumulates_token_usage():
    agent = _AddsFlagAgent(llm_provider=MockProvider(script=["a response here"]))
    state = ComplianceState()

    from compliance_copilot.llm.base import LLMMessage

    agent.call_llm(state, [LLMMessage(role="user", content="hi there")])

    assert state.token_usage > 0
