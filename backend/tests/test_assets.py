"""Unit tests for asset domain — pure logic, no DB or Ollama."""

import hashlib

from app.domains.assets.service import compute_content_hash, next_version_num


# ── compute_content_hash ──────────────────────────────────────────────────────


def test_content_hash_is_sha256_hex():
    content = "You are a helpful assistant."
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert compute_content_hash(content) == expected


def test_content_hash_length():
    # SHA-256 produces 64 hex characters
    assert len(compute_content_hash("anything")) == 64


def test_content_hash_deterministic():
    content = "system prompt v1"
    assert compute_content_hash(content) == compute_content_hash(content)


def test_content_hash_differs_for_different_content():
    assert compute_content_hash("prompt A") != compute_content_hash("prompt B")


def test_content_hash_unicode():
    # Non-ASCII content should hash without error
    result = compute_content_hash("Ünïcödé prömpt 🤖")
    assert len(result) == 64


# ── next_version_num ──────────────────────────────────────────────────────────


def test_next_version_num_empty_returns_one():
    assert next_version_num([]) == 1


def test_next_version_num_sequential():
    assert next_version_num([1]) == 2
    assert next_version_num([1, 2]) == 3
    assert next_version_num([1, 2, 3]) == 4


def test_next_version_num_out_of_order():
    # Should still be max + 1, not len + 1
    assert next_version_num([3, 1, 2]) == 4


def test_next_version_num_does_not_mutate():
    nums = [1, 2, 3]
    next_version_num(nums)
    assert nums == [1, 2, 3]


def test_next_version_num_single_high():
    assert next_version_num([99]) == 100


# ── validate_eval_cases (KC-042) ──────────────────────────────────────────────

import pytest
from fastapi import HTTPException

from app.domains.assets.service import validate_eval_cases
from app.schemas.asset import EvalCaseIn


def _case(**kw):
    defaults = {"input": "What is 2+2?", "expected_output": "4"}
    return EvalCaseIn(**{**defaults, **kw})


def test_valid_cases_pass():
    validate_eval_cases([
        _case(),
        _case(grading_strategy="contains"),
        _case(grading_strategy="regex", grading_config={"pattern": r"\b4\b"}),
        _case(grading_strategy="llm_judge"),
    ])


def test_blank_input_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_eval_cases([_case(input="   ")])
    assert exc.value.status_code == 422
    assert "eval_cases[0]" in exc.value.detail


def test_blank_expected_output_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_eval_cases([_case(expected_output="")])
    assert exc.value.status_code == 422


def test_unknown_strategy_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_eval_cases([_case(grading_strategy="vibes")])
    assert exc.value.status_code == 422
    assert "grading_strategy" in exc.value.detail


def test_invalid_regex_pattern_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_eval_cases([_case(grading_strategy="regex", grading_config={"pattern": "("})])
    assert exc.value.status_code == 422
    assert "invalid regex" in exc.value.detail


def test_regex_falls_back_to_expected_output_as_pattern():
    # expected_output "(" is an invalid pattern when no config is given
    with pytest.raises(HTTPException):
        validate_eval_cases([_case(expected_output="(", grading_strategy="regex")])
    # but a valid expected_output compiles fine
    validate_eval_cases([_case(expected_output="4", grading_strategy="regex")])


def test_error_indexes_the_offending_case():
    with pytest.raises(HTTPException) as exc:
        validate_eval_cases([_case(), _case(input=" ")])
    assert "eval_cases[1]" in exc.value.detail
