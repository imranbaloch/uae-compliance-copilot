"""Example: run the full pipeline against the bundled sample data.

Usage:
    python examples/run_sample.py

By default this uses whatever LLM_PROVIDER is configured in your environment
(see .env.example). With no .env at all, it defaults to Ollama at
http://localhost:11434 — start `ollama serve` and `ollama pull llama3.1`
first, or export LLM_PROVIDER=openai / anthropic / groq with an API key, or
set LLM_PROVIDER=mock to run with no LLM at all (deterministic fallbacks only).
"""

from __future__ import annotations

import json
from pathlib import Path

from compliance_copilot.agents.supervisor import Supervisor
from compliance_copilot.config import get_settings
from compliance_copilot.logging_config import configure_logging

SAMPLE_PATH = Path(__file__).parent / "sample_data" / "sample_input.json"


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    raw_input = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    result = Supervisor().run_pipeline(raw_input)
    state = result.state

    print(f"\nPlan: {state.plan}\n")
    print(f"Executed nodes: {result.executed}")
    print(f"Skipped nodes:  {result.skipped}")
    print(f"Failed nodes:   {result.failed}\n")

    if state.report:
        print(json.dumps(state.report.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
