# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-07-29

### Added
- FastAPI JSON API (`api/routes.py`): `POST /api/reports`, `POST /api/reports/upload`,
  `GET /api/reports`, `GET /api/reports/{id}` -- a pure consumer of `Supervisor`, no changes to core agent code.
- Server-rendered HTML dashboard (`api/web.py` + `api/templates/`): upload a JSON file or try sample data, view a
  rendered report with risk score, findings tables, and recommended actions.
- SQLite-backed report persistence (`api/store.py`), no ORM.
- `api` optional dependency group (`pip install -e ".[dev,api]"`) and `make api` entry point.
- 12 new integration tests (`tests/integration/test_api.py`) covering the API and web routes with a
  `MockProvider`-backed Supervisor injected via FastAPI dependency overrides.

## [0.1.0] - 2026-07-29

Initial release.

### Added
- Supervisor agent + five composable specialist agents (Intake, Tax Compliance,
  Anomaly Detection, Sanctions/PEP Screening, Report Synthesis) orchestrated via
  a custom lightweight DAG engine (`src/compliance_copilot/graph`).
- LLM provider abstraction (`src/compliance_copilot/llm`) supporting OpenAI,
  Anthropic, Ollama, Azure OpenAI, Groq, and any custom OpenAI-compatible
  endpoint, fully configurable via environment variables with per-role
  (orchestrator/sub-agent) overrides for hybrid cloud+local deployments.
- Deterministic rules engines for UAE VAT/e-invoicing field validation
  (`tools/tax_rules.py`) and reconciliation anomaly detection
  (`tools/anomaly_rules.py`), plus a fuzzy sanctions/PEP screening tool
  (`tools/sanctions_list.py`) with a bundled sample list.
- Shared `ComplianceState` memory layer threaded through the agent graph.
- `MockProvider` test double enabling a full test suite with zero network
  access or API keys.
- CLI entry point (`compliance-copilot`) and two runnable examples
  (`examples/run_sample.py`, `examples/run_with_mock.py`).
- 93 tests (unit + integration), 94% statement coverage.
- `docs/research.md`, `docs/validation.md`, `docs/architecture.md` documenting
  the UAE pain-point research, idea validation, and system design.
