"""Command-line entry point: `compliance-copilot <input.json>`."""

from __future__ import annotations

import json
import sys

from compliance_copilot.agents.supervisor import Supervisor
from compliance_copilot.config import get_settings
from compliance_copilot.logging_config import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    if len(sys.argv) < 2:
        print("Usage: compliance-copilot <path/to/input.json>", file=sys.stderr)
        raise SystemExit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        raw_input = json.load(f)

    result = Supervisor().run_pipeline(raw_input)
    state = result.state

    print(f"\nPlan: {state.plan}\n")
    print(f"Executed: {result.executed}")
    print(f"Skipped:  {result.skipped}")
    print(f"Failed:   {result.failed}\n")

    if state.report:
        print(json.dumps(state.report.model_dump(mode="json"), indent=2, default=str))
    else:
        print("No report was produced.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
