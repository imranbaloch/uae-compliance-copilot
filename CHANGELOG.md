# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-07-29

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
