from __future__ import annotations

from compliance_copilot.memory.state import ComplianceState


def test_new_state_is_empty():
    state = ComplianceState()
    assert state.invoices == []
    assert state.errors == []
    assert state.report is None


def test_record_error_appends():
    state = ComplianceState()
    state.record_error("agent_x", "boom", retryable=True)
    assert len(state.errors) == 1
    assert state.errors[0].agent == "agent_x"
    assert state.errors[0].retryable is True


def test_mark_complete_is_idempotent():
    state = ComplianceState()
    state.mark_complete("intake")
    state.mark_complete("intake")
    assert state.completed_agents == ["intake"]
