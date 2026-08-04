"""Unit tests for eval worker grading — pure logic, no DB, no Ollama.

Covers app.worker.eval._normalize and _grade (all strategies). The async
llm_judge path (_grade_llm) requires Ollama and is exercised in live runs;
_grade's llm_judge branch is asserted to be a safe no-op fallback.
"""

from app.worker.eval import _grade, _normalize

# ── _normalize ────────────────────────────────────────────────────────────────


def test_normalize_strips_and_lowercases():
    assert _normalize("  Paris  ") == "paris"


def test_normalize_collapses_internal_whitespace():
    assert _normalize("New\t York   City") == "new york city"


def test_normalize_strips_edge_punctuation():
    assert _normalize("Paris.") == "paris"
    assert _normalize("(Paris)") == "paris"
    assert _normalize("'Paris!'") == "paris"


def test_normalize_keeps_internal_punctuation():
    assert _normalize("it's Paris, France") == "it's paris, france"


def test_normalize_unicode_nfc():
    composed = "ñ"      # single code point (NFC)
    decomposed = "ñ"  # n + combining tilde (NFD)
    assert _normalize(composed) == _normalize(decomposed)


def test_normalize_smart_quotes_fold_to_straight():
    assert _normalize("“Paris”") == _normalize('"Paris"')
    assert _normalize("‘Paris’") == _normalize("'Paris'")


# ── exact_match ───────────────────────────────────────────────────────────────


def test_exact_match_pass_after_normalisation():
    assert _grade(" Tokyo. ", "tokyo", "exact_match", None) is True


def test_exact_match_fails_on_extra_words():
    assert _grade("The capital is Tokyo", "Tokyo", "exact_match", None) is False


def test_exact_match_fails_on_wrong_answer():
    assert _grade("Paris", "Berlin", "exact_match", None) is False


# ── contains ──────────────────────────────────────────────────────────────────


def test_contains_pass_within_sentence():
    assert _grade("The capital of France is Paris.", "Paris", "contains", None) is True


def test_contains_normalises_both_sides():
    assert _grade("PARIS is the answer", " paris ", "contains", None) is True


def test_contains_fails_when_absent():
    assert _grade("The capital is Berlin.", "Paris", "contains", None) is False


# ── regex ─────────────────────────────────────────────────────────────────────


def test_regex_uses_config_pattern():
    assert _grade("Paris, obviously", "ignored", "regex", {"pattern": "paris"}) is True


def test_regex_falls_back_to_expected_when_no_config():
    assert _grade("It is Paris", "Par.s", "regex", None) is True
    assert _grade("It is Paris", "Par.s", "regex", {}) is True


def test_regex_is_case_insensitive_on_raw_actual():
    assert _grade("PARIS", "paris", "regex", None) is True


def test_regex_fails_when_pattern_absent():
    assert _grade("Berlin", "paris", "regex", {"pattern": "paris"}) is False


# ── llm_judge + unknown strategies ────────────────────────────────────────────


def test_llm_judge_branch_in_grade_is_safe_fallback():
    # llm_judge is graded via the async _grade_llm path; the sync _grade
    # branch must never accidentally pass.
    assert _grade("yes", "yes", "llm_judge", None) is False


def test_unknown_strategy_returns_false():
    assert _grade("Paris", "Paris", "made_up_strategy", None) is False
