"""Sanctions/PEP Screening Agent.

Fuzzy-matches each known counterparty against the bundled sample sanctions/PEP
list (swappable for a live feed — see `tools/sanctions_list.py`). Deliberately
deterministic (no LLM call) for the matching step itself: screening decisions
should be reproducible and auditable, not subject to LLM sampling variance.
Ambiguous/borderline hits are flagged `requires_review=True` rather than
auto-cleared or auto-blocked.
"""

from __future__ import annotations

from compliance_copilot.agents.base import BaseAgent
from compliance_copilot.memory.state import ComplianceState, SanctionsHit
from compliance_copilot.tools.sanctions_list import load_sanctions_list, screen_name

AUTO_CLEAR_MARGIN = 10.0  # score points above threshold considered a confident match


class SanctionsScreeningAgent(BaseAgent):
    name = "sanctions_screening"
    role = "subagent"

    def run(self, state: ComplianceState) -> ComplianceState:
        threshold = float(self.settings.sanctions_match_threshold)
        sanctions_list = load_sanctions_list()

        for counterparty in state.counterparties:
            hits = screen_name(
                counterparty.name, sanctions_list=sanctions_list, threshold=threshold
            )
            for entry, score in hits:
                state.sanctions_hits.append(
                    SanctionsHit(
                        counterparty_name=counterparty.name,
                        matched_name=entry.name,
                        list_source=sanctions_list.list_source,
                        score=round(score, 1),
                        requires_review=score < (threshold + AUTO_CLEAR_MARGIN),
                    )
                )

        self.log.info(
            "sanctions_screening_complete",
            screened=len(state.counterparties),
            hits=len(state.sanctions_hits),
        )
        return state
