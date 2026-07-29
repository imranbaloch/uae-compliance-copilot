from __future__ import annotations

import pytest

from compliance_copilot.graph.engine import GraphCycleError, GraphEngine


def test_executes_nodes_in_dependency_order():
    order: list[str] = []

    def make(name):
        def _fn(state):
            order.append(name)
            return state

        return _fn

    graph: GraphEngine[list] = GraphEngine()
    graph.add_node("a", make("a"))
    graph.add_node("b", make("b"), depends_on=["a"])
    graph.add_node("c", make("c"), depends_on=["a"])
    graph.add_node("d", make("d"), depends_on=["b", "c"])

    result = graph.run([])

    assert order[0] == "a"
    assert order[-1] == "d"
    assert set(order[1:3]) == {"b", "c"}
    assert result.executed == order
    assert result.failed == []
    assert result.skipped == []


def test_condition_skips_node():
    graph: GraphEngine[dict] = GraphEngine()
    graph.add_node("a", lambda s: {**s, "a": True})
    graph.add_node("b", lambda s: {**s, "b": True}, depends_on=["a"], condition=lambda s: False)

    result = graph.run({})

    assert "a" in result.executed
    assert "b" in result.skipped
    assert result.state == {"a": True}


def test_failed_node_is_isolated_and_dependents_still_run():
    def boom(state):
        raise ValueError("kaboom")

    calls = []

    graph: GraphEngine[dict] = GraphEngine()
    graph.add_node("a", boom)
    graph.add_node("b", lambda s: calls.append("b") or s, depends_on=["a"])

    result = graph.run({})

    assert result.failed == ["a"]
    assert result.executed == ["b"]
    assert calls == ["b"]


def test_duplicate_node_name_raises():
    graph: GraphEngine[dict] = GraphEngine()
    graph.add_node("a", lambda s: s)
    with pytest.raises(ValueError):
        graph.add_node("a", lambda s: s)


def test_unknown_dependency_raises():
    graph: GraphEngine[dict] = GraphEngine()
    graph.add_node("a", lambda s: s, depends_on=["missing"])
    with pytest.raises(ValueError):
        graph.run({})


def test_cycle_detection():
    graph: GraphEngine[dict] = GraphEngine()
    graph.add_node("a", lambda s: s, depends_on=["b"])
    graph.add_node("b", lambda s: s, depends_on=["a"])
    with pytest.raises(GraphCycleError):
        graph.run({})
