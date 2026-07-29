"""Shared logic for turning raw input into a stored `ReportEnvelope`.

Both the JSON API routes and the HTML web routes call `run_pipeline_and_store`
so there is exactly one code path that touches the `Supervisor` and the
database — the two route modules only differ in how they parse the request
and how they render the response.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from api import store
from api.schemas import ReportEnvelope
from compliance_copilot.agents.supervisor import Supervisor


def run_pipeline_and_store(raw_input: dict, supervisor: Supervisor) -> ReportEnvelope:
    """Run the agent pipeline synchronously and persist the result.

    This performs blocking LLM calls — callers running inside an async
    framework (FastAPI) should invoke this via `starlette.concurrency.run_in_threadpool`
    so it doesn't block the event loop.
    """
    result = supervisor.run_pipeline(raw_input)
    state = result.state

    if state.report is None:
        # report_synthesis itself failed unexpectedly (should be rare — it has
        # its own internal fallbacks) — surface a minimal error report rather
        # than a 500, so the caller always gets a well-formed response.
        from compliance_copilot.memory.state import ComplianceReport

        state.report = ComplianceReport(
            risk_score=0,
            summary="The pipeline could not produce a report. See errors for details.",
            errors=state.errors,
        )

    envelope = ReportEnvelope(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        plan=state.plan,
        executed=result.executed,
        skipped=result.skipped,
        failed=result.failed,
        report=state.report,
    )
    store.save_report(envelope.model_dump(mode="json"))
    return envelope
