"""Lightweight SQLite-backed storage for pipeline run results.

Deliberately stdlib-only (no ORM) to keep the API layer's dependency
footprint small, matching the core library's "lightweight dependencies"
philosophy. Each row stores one `ReportEnvelope` as a JSON blob -- the schema
is intentionally minimal since `ComplianceReport` is already a structured,
versioned Pydantic model; we don't need to normalize it into columns.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("API_DB_PATH", "compliance_copilot_api.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    summary TEXT NOT NULL,
    envelope_json TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the reports table if it doesn't exist yet. Safe to call repeatedly."""
    with _connect() as conn:
        conn.execute(_SCHEMA)


def save_report(envelope: dict) -> str:
    """Persist a report envelope (already-serialized dict) and return its id."""
    report_id = envelope.get("id") or str(uuid.uuid4())
    envelope["id"] = report_id
    envelope.setdefault("created_at", datetime.now(timezone.utc).isoformat())

    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reports (id, created_at, risk_score, summary, envelope_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                report_id,
                envelope["created_at"],
                envelope["report"]["risk_score"],
                envelope["report"]["summary"],
                json.dumps(envelope),
            ),
        )
    return report_id


def get_report(report_id: str) -> dict | None:
    """Fetch a single report envelope by id, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT envelope_json FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
    return json.loads(row["envelope_json"]) if row else None


def list_reports(limit: int = 50) -> list[dict]:
    """List recent report summaries (id, created_at, risk_score, summary), newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, risk_score, summary FROM reports "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
