"""FastAPI dependency providers.

Kept in one place so tests can override `get_supervisor` with a
`MockProvider`-backed instance via `app.dependency_overrides`, without any
network access or API keys.
"""

from __future__ import annotations

from compliance_copilot.agents.supervisor import Supervisor


def get_supervisor() -> Supervisor:
    """Build a `Supervisor` using whatever LLM_PROVIDER is configured in the
    environment (see .env.example). Overridden in tests."""
    return Supervisor()
