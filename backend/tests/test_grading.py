"""Unit tests for MC answer grading normalisation — pure logic, no DB."""

import pytest

from app.domains.learning.service import _normalize_answer


# ── _normalize_answer ─────────────────────────────────────────────────────────


def test_normalize_strips_whitespace():
    assert _normalize_answer("  Durability  ") == "durability"


def test_normalize_lowercases():
    assert _normalize_answer("HTTPS") == "https"


def test_normalize_collapses_internal_whitespace():
    assert _normalize_answer("write  ahead  logging") == "write ahead logging"


def test_normalize_strips_leading_trailing_punctuation():
    assert _normalize_answer(".Durability.") == "durability"
    assert _normalize_answer("(answer)") == "answer"


def test_normalize_unicode_nfc():
    # NFC: composed form — ñ as single code point vs n + combining tilde
    composed = "ñ"      # ñ (NFC)
    decomposed = "ñ"  # n + combining tilde (NFD)
    assert _normalize_answer(composed) == _normalize_answer(decomposed)


def test_normalize_smart_quotes():
    # Smart quotes and straight quotes should normalise the same
    assert _normalize_answer("“caching”") == _normalize_answer('"caching"')


# ── Grading behaviour (via _normalize_answer logic) ──────────────────────────
# These verify the contract: normalised exact-match only — no fuzzy threshold.


def test_similar_wrong_answer_is_not_correct():
    """HTTP vs HTTPS — textually close but semantically different; must grade wrong."""
    assert _normalize_answer("HTTP") != _normalize_answer("HTTPS")


def test_singular_vs_plural_grades_wrong():
    """'increase' vs 'increases' — a threshold-based fuzzy match would pass this incorrectly."""
    assert _normalize_answer("increase") != _normalize_answer("increases")


def test_normalised_equals_match():
    """Two representations of the same answer that should grade correct."""
    assert _normalize_answer("  Write-Ahead Logging. ") == _normalize_answer("write-ahead logging")


def test_empty_answer_normalises_to_empty():
    assert _normalize_answer("   ") == ""
