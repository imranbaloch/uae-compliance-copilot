"""JSON API routes: `/api/reports`.

All endpoints delegate the actual agent work to `api.service.run_pipeline_and_store`,
running it in a worker thread (`run_in_threadpool`) since the Supervisor's LLM
calls are synchronous — this keeps the event loop free to serve other
requests concurrently without requiring the agent core to be rewritten async.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from api import store
from api.deps import get_supervisor
from api.schemas import PipelineRequest, ReportEnvelope, ReportSummary
from api.service import run_pipeline_and_store
from compliance_copilot.agents.supervisor import Supervisor
from compliance_copilot.logging_config import get_logger

router = APIRouter(prefix="/api", tags=["reports"])
_log = get_logger("api")


@router.post("/reports", response_model=ReportEnvelope)
async def create_report(
    request: PipelineRequest, supervisor: Supervisor = Depends(get_supervisor)
) -> ReportEnvelope:
    """Run the compliance pipeline against the given invoices/transactions/counterparties."""
    raw_input = request.model_dump()
    envelope = await run_in_threadpool(run_pipeline_and_store, raw_input, supervisor)
    _log.info("report_created", report_id=envelope.id, risk_score=envelope.report.risk_score)
    return envelope


@router.post("/reports/upload", response_model=ReportEnvelope)
async def upload_report(
    file: UploadFile, supervisor: Supervisor = Depends(get_supervisor)
) -> ReportEnvelope:
    """Same as `POST /api/reports`, but accepts a JSON file upload (the same
    shape as `examples/sample_data/sample_input.json`)."""
    raw_bytes = await file.read()
    try:
        raw_input = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"Uploaded file is not valid JSON: {exc}"
        ) from exc

    if not isinstance(raw_input, dict):
        raise HTTPException(
            status_code=400,
            detail="Uploaded JSON must be an object with "
            "'invoices'/'transactions'/'counterparties' keys.",
        )

    envelope = await run_in_threadpool(run_pipeline_and_store, raw_input, supervisor)
    _log.info("report_created_from_upload", report_id=envelope.id, filename=file.filename)
    return envelope


@router.get("/reports", response_model=list[ReportSummary])
async def list_reports() -> list[dict]:
    """List recent report runs, most recent first."""
    return store.list_reports()


@router.get("/reports/{report_id}", response_model=ReportEnvelope)
async def get_report(report_id: str) -> dict:
    """Fetch one report by id."""
    envelope = store.get_report(report_id)
    if envelope is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return envelope
