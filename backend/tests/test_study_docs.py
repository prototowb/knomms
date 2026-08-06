"""Unit tests for study-doc composition — pure logic, no DB or I/O (KC-076)."""

from app.domains.harnesses.study_docs import (
    compose_eval_run_doc,
    compose_eval_suite_doc,
    compose_slot_doc,
)


# ── compose_slot_doc ──────────────────────────────────────────────────────────


def test_slot_doc_includes_role_title_version_and_content():
    doc = compose_slot_doc(
        role="system_prompt",
        asset_title="Support triage prompt",
        asset_description="Routes tickets by severity.",
        version_num=3,
        model_pin="mistral:7b-instruct",
        rationale="v3 adds explicit severity rubric.",
        content="You are a triage assistant. Classify each ticket.",
    )
    assert "system prompt" in doc  # humanized role
    assert "Support triage prompt" in doc
    assert "version 3" in doc
    assert "mistral:7b-instruct" in doc
    assert "v3 adds explicit severity rubric." in doc
    assert "You are a triage assistant. Classify each ticket." in doc


def test_slot_doc_omits_empty_optional_fields():
    doc = compose_slot_doc(
        role="few_shot_set",
        asset_title="Examples",
        asset_description="   ",
        version_num=1,
        model_pin=None,
        rationale="",
        content="Example 1: ...",
    )
    assert "Asset description" not in doc
    assert "pinned to the model" not in doc
    assert "Version rationale" not in doc
    assert "Example 1: ..." in doc


# ── compose_eval_suite_doc ────────────────────────────────────────────────────


def test_eval_suite_doc_lists_every_case_with_strategy():
    doc = compose_eval_suite_doc(
        harness_title="Triage harness",
        asset_title="Triage eval suite",
        version_num=2,
        cases=[
            {"input": "Server down!", "expected_output": "sev1", "grading_strategy": "exact_match"},
            {"input": "Typo on page", "expected_output": "sev4", "grading_strategy": "contains"},
        ],
    )
    assert "Triage harness" in doc
    assert "2 test case(s)" in doc
    assert "Case 1 (graded by exact_match)" in doc
    assert '"Server down!"' in doc
    assert "Case 2 (graded by contains)" in doc
    assert '"sev4"' in doc


def test_eval_suite_doc_zero_cases():
    doc = compose_eval_suite_doc("H", "Suite", 1, cases=[])
    assert "0 test case(s)" in doc


# ── compose_eval_run_doc ──────────────────────────────────────────────────────


def _metrics(**overrides) -> dict:
    base = {
        "total": 2,
        "passed": 1,
        "failed": 1,
        "pass_rate": 0.5,
        "provider": "ollama",
        "results": [
            {
                "case_id": "c1",
                "passed": True,
                "actual_output": "sev1",
                "latency_ms": 812,
                "grading_strategy": "exact_match",
            },
            {
                "case_id": "c2",
                "passed": False,
                "actual_output": "sev2 — needs escalation",
                "latency_ms": 903,
                "grading_strategy": "exact_match",
            },
        ],
    }
    base.update(overrides)
    return base


def test_eval_run_doc_summarises_pass_rate_and_failures():
    doc = compose_eval_run_doc(
        harness_title="Triage harness",
        model_pin="mistral:7b-instruct",
        provider="ollama",
        created_at="2026-08-06",
        metrics=_metrics(),
    )
    assert "pass rate of 50.0%" in doc
    assert "Case 1 passed" in doc
    assert "Case 2 FAILED" in doc
    # Failed cases include the actual output — that is the teachable material
    assert "sev2 — needs escalation" in doc
    # Passed cases don't dump outputs
    assert doc.count("actual output") == 1


def test_eval_run_doc_includes_case_errors():
    metrics = _metrics()
    metrics["results"][1] = {
        "case_id": "c2",
        "passed": False,
        "actual_output": "",
        "latency_ms": 0,
        "grading_strategy": "contains",
        "error": "Ollama timeout after 3 attempts",
    }
    doc = compose_eval_run_doc("H", "m", "ollama", "2026-08-06", metrics)
    assert "Error: Ollama timeout after 3 attempts" in doc


def test_eval_run_doc_includes_token_usage_when_present():
    metrics = _metrics(usage={"input_tokens": 1200, "output_tokens": 340})
    doc = compose_eval_run_doc("H", "claude-x", "anthropic", "2026-08-06", metrics)
    assert "1200 input tokens" in doc
    assert "340 output tokens" in doc


def test_eval_run_doc_truncates_long_actual_output():
    metrics = _metrics()
    metrics["results"][1]["actual_output"] = "x" * 500
    doc = compose_eval_run_doc("H", "m", "ollama", "2026-08-06", metrics)
    assert "x" * 300 in doc
    assert "x" * 301 not in doc


def test_eval_run_doc_tolerates_missing_results():
    doc = compose_eval_run_doc(
        "H", "m", "ollama", "2026-08-06", {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}
    )
    assert "graded 0 case(s)" in doc
