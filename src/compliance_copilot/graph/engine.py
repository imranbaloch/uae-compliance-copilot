"""A minimal DAG orchestration engine.

Deliberately not LangGraph/AutoGen/CrewAI: the pipeline here is a fixed,
shallow DAG (intake -> parallel specialists -> synthesis) with no need for
cyclic re-planning or streaming token graphs. This ~150-line topological
executor gives the same core guarantees (explicit node dependencies,
per-node error isolation, shared-state passing, conditional/optional nodes)
without adding a large dependency. See `docs/architecture.md` for the full
rationale — the `GraphEngine.run()` contract is narrow enough that a
heavier engine could be substituted later without touching agent code.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from compliance_copilot.logging_config import get_logger

StateT = TypeVar("StateT")

NodeFn = Callable[[StateT], StateT]
ConditionFn = Callable[[StateT], bool]

_log = get_logger("graph.engine")


@dataclass
class Node(Generic[StateT]):
    """A single unit of work in the graph.

    Attributes:
        name: Unique node name.
        fn: Function that takes the current state and returns an updated state.
        depends_on: Names of nodes that must complete (successfully or not)
            before this node runs.
        condition: Optional predicate; if it returns False the node is skipped
            entirely (used e.g. to skip sanctions screening when no
            counterparties were supplied).
    """

    name: str
    fn: NodeFn
    depends_on: list[str] = field(default_factory=list)
    condition: ConditionFn | None = None


class GraphCycleError(Exception):
    """Raised when the graph contains a cycle and cannot be topologically sorted."""


@dataclass
class ExecutionResult(Generic[StateT]):
    """Outcome of a full graph run."""

    state: StateT
    executed: list[str]
    skipped: list[str]
    failed: list[str]


class GraphEngine(Generic[StateT]):
    """Lightweight DAG executor over a shared state object."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node[StateT]] = {}

    def add_node(
        self,
        name: str,
        fn: NodeFn,
        *,
        depends_on: list[str] | None = None,
        condition: ConditionFn | None = None,
    ) -> None:
        """Register a node. Raises ``ValueError`` on duplicate names."""
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already registered")
        self._nodes[name] = Node(name=name, fn=fn, depends_on=depends_on or [], condition=condition)

    def _topological_order(self) -> list[str]:
        visited: dict[str, int] = {}  # 0 = visiting, 1 = done
        order: list[str] = []

        def visit(name: str, stack: tuple[str, ...]) -> None:
            if name not in self._nodes:
                raise ValueError(f"Node '{name}' depends on unknown node '{name}'")
            state = visited.get(name)
            if state == 1:
                return
            if state == 0:
                raise GraphCycleError(f"Cycle detected: {' -> '.join([*stack, name])}")
            visited[name] = 0
            for dep in self._nodes[name].depends_on:
                if dep not in self._nodes:
                    raise ValueError(f"Node '{name}' depends on unknown node '{dep}'")
                visit(dep, (*stack, name))
            visited[name] = 1
            order.append(name)

        for name in self._nodes:
            visit(name, ())
        return order

    def run(self, state: StateT) -> ExecutionResult[StateT]:
        """Execute all nodes in dependency order.

        A node whose `condition` evaluates False is skipped (its dependents
        still run). A node that raises is recorded as failed and its
        dependents still run against the unmodified state — callers should
        design agent functions to record errors on `state` rather than raise
        where possible (see `BaseAgent`), so downstream synthesis can report
        partial results.
        """
        order = self._topological_order()
        executed: list[str] = []
        skipped: list[str] = []
        failed: list[str] = []

        for name in order:
            node = self._nodes[name]
            if node.condition is not None and not node.condition(state):
                _log.info("node_skipped", node=name)
                skipped.append(name)
                continue
            try:
                _log.info("node_start", node=name)
                state = node.fn(state)
                executed.append(name)
                _log.info("node_done", node=name)
            except Exception as exc:  # noqa: BLE001 - intentional: isolate node failures
                _log.error("node_failed", node=name, error=str(exc))
                failed.append(name)

        return ExecutionResult(state=state, executed=executed, skipped=skipped, failed=failed)
