"""HTML dashboard: upload a file, watch it run, view the report.

Server-rendered with Jinja2 — no separate frontend build step, no JS
framework dependency, consistent with the project's lightweight-dependency
philosophy. Uses the same `run_pipeline_and_store` service function as the
JSON API, so behavior is identical between the two surfaces.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from api import store
from api.deps import get_supervisor
from api.service import run_pipeline_and_store
from compliance_copilot.agents.supervisor import Supervisor

router = APIRouter(prefix="/web", tags=["dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

SAMPLE_INPUT_PATH = Path(__file__).parent.parent / "examples" / "sample_data" / "sample_input.json"


def _risk_level(score: int) -> str:
    if score < 20:
        return "low"
    if score < 50:
        return "moderate"
    return "high"


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    reports = store.list_reports()
    return templates.TemplateResponse(request, "index.html", {"reports": reports})


@router.post("/reports")
async def submit_report(
    request: Request, file: UploadFile, supervisor: Supervisor = Depends(get_supervisor)
):
    raw_bytes = await file.read()
    try:
        raw_input = json.loads(raw_bytes) if raw_bytes else {}
    except json.JSONDecodeError:
        reports = store.list_reports()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "reports": reports,
                "error": "That file isn't valid JSON. Check the format and try again.",
            },
            status_code=400,
        )

    envelope = await run_in_threadpool(run_pipeline_and_store, raw_input, supervisor)
    return RedirectResponse(url=f"/web/reports/{envelope.id}", status_code=303)


@router.post("/reports/sample")
async def submit_sample(request: Request, supervisor: Supervisor = Depends(get_supervisor)):
    raw_input = json.loads(SAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
    envelope = await run_in_threadpool(run_pipeline_and_store, raw_input, supervisor)
    return RedirectResponse(url=f"/web/reports/{envelope.id}", status_code=303)


@router.get("/reports/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: str) -> HTMLResponse:
    envelope = store.get_report(report_id)
    if envelope is None:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"reports": store.list_reports(), "error": f"Report '{report_id}' not found."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "report.html",
        {"envelope": envelope, "risk_level": _risk_level(envelope["report"]["risk_score"])},
    )
