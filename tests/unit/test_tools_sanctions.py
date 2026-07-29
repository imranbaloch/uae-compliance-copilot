from __future__ import annotations

from compliance_copilot.tools.sanctions_list import (
    load_sanctions_list,
    name_similarity,
    screen_name,
)


def test_load_sample_sanctions_list_has_entries():
    sanctions_list = load_sanctions_list()
    assert sanctions_list.entries
    assert any(e.name == "Al Farooq Trading FZE" for e in sanctions_list.entries)


def test_name_similarity_exact_match_is_100():
    assert name_similarity("Al Farooq Trading FZE", "Al Farooq Trading FZE") == 100.0


def test_name_similarity_is_case_insensitive():
    assert name_similarity("al farooq trading fze", "AL FAROOQ TRADING FZE") == 100.0


def test_screen_name_finds_exact_match():
    hits = screen_name("Al Farooq Trading FZE", threshold=85.0)
    assert len(hits) == 1
    entry, score = hits[0]
    assert entry.name == "Al Farooq Trading FZE"
    assert score == 100.0


def test_screen_name_no_match_for_unrelated_name():
    hits = screen_name("Totally Unrelated Bakery LLC", threshold=85.0)
    assert hits == []


def test_screen_name_respects_threshold():
    # A partial/fuzzy variant should match at a low threshold but not a high one
    hits_loose = screen_name("Al Farooq Trading", threshold=50.0)
    hits_strict = screen_name("Al Farooq Trading", threshold=99.0)
    assert len(hits_loose) >= 1
    assert hits_strict == []


def test_screen_name_results_sorted_descending():
    hits = screen_name("Al Farooq Trading FZE", threshold=1.0)
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)
