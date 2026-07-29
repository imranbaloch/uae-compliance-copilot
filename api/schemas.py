"""Request/response models for the API layer.

`ComplianceReport` itself is reused directly from the core library (it's
already a Pydantic model) — this module only adds the thin request envelope
and the response wrapper that carries run metadata (plan, which nodes ran)
alongside the report.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from compliance_copilot.memory.state import ComplianceReport


class PipelineRequest(BaseModel):
    """Raw input for a pipeline run — same shape as `examples/sample_data/sample_input.json`."""

    invoices: list[dict] = Field(default_factory=list)
    transactions: list[dict] = Field(default_factory=list)
    counterparties: list[dict] = Field(default_factory=list)


class ReportEnvelope(BaseModel):
    """A stored/returned pipeline run: the report plus execution metadata."""

    id: str
    created_at: datetime
    plan: str | None = None
    executed: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    report: ComplianceReport


class ReportSummary(BaseModel):
    """A lightweight listing entry, without the full findings payload."""

    id: str
    created_at: datetime
    risk_score: int
    summary: str
