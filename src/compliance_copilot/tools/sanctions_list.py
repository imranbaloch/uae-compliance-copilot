"""Sanctions/PEP fuzzy-matching tool.

Ships with a small bundled sample list (`data/sample_sanctions_list.json`) so
the project is fully runnable/testable offline. In production this module is
meant to be pointed at a real consolidated list (UN, OFAC SDN, local FIU feed)
by swapping `load_sanctions_list`'s source — the matching logic is unchanged.
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from functools import lru_cache
from importlib import resources
from pathlib import Path

from pydantic import BaseModel


class SanctionsEntry(BaseModel):
    name: str
    country: str | None = None
    entity_type: str = "organization"


class SanctionsList(BaseModel):
    list_source: str
    entries: list[SanctionsEntry]


@lru_cache
def load_sanctions_list(path: str | None = None) -> SanctionsList:
    """Load the sanctions/PEP list from a JSON file.

    Args:
        path: Optional explicit path to a JSON file with the same shape as
            `data/sample_sanctions_list.json`. Defaults to the bundled sample.
    """
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        ref = resources.files("compliance_copilot.tools.data").joinpath(
            "sample_sanctions_list.json"
        )
        data = json.loads(ref.read_text(encoding="utf-8"))
    return SanctionsList(**data)


def name_similarity(a: str, b: str) -> float:
    """Return a 0-100 fuzzy similarity score between two names."""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio() * 100


def screen_name(
    name: str,
    *,
    sanctions_list: SanctionsList | None = None,
    threshold: float = 85.0,
) -> list[tuple[SanctionsEntry, float]]:
    """Screen a single counterparty name against the sanctions/PEP list.

    Returns:
        A list of `(entry, score)` tuples for entries scoring at or above
        `threshold`, sorted by descending score.
    """
    sanctions_list = sanctions_list or load_sanctions_list()
    hits = [(entry, name_similarity(name, entry.name)) for entry in sanctions_list.entries]
    hits = [(entry, score) for entry, score in hits if score >= threshold]
    hits.sort(key=lambda pair: pair[1], reverse=True)
    return hits
