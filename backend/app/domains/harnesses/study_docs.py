"""Study-doc composition — pure functions, no DB, no I/O (docs/12, KC-076).

Each function renders one harness facet as a plain-text/markdown document to
be ingested as its own Source. One-source-per-facet is load-bearing: the
curriculum agent groups concepts per source (KC-074), so each document here
becomes (at least) one concept in the generated learning path.

Kept import-isolated from ORM/service modules so the unit suite can exercise
composition with plain values (same rationale as learning/types.py).
"""

_ACTUAL_OUTPUT_EXCERPT = 300


def compose_slot_doc(
    role: str,
    asset_title: str,
    asset_description: str,
    version_num: int,
    model_pin: str | None,
    rationale: str,
    content: str,
) -> str:
    """Render one harness slot (an asset version) as a study document."""
    lines = [
        f"Harness slot: {_humanize(role)} — {asset_title} (version {version_num})",
        "",
        f"This document describes the '{role}' slot of the harness. "
        f"It contains version {version_num} of the asset \"{asset_title}\".",
    ]
    if asset_description.strip():
        lines += ["", f"Asset description: {asset_description.strip()}"]
    if model_pin:
        lines += ["", f"This version is pinned to the model '{model_pin}'."]
    if rationale.strip():
        lines += ["", f"Version rationale: {rationale.strip()}"]
    lines += ["", "Full content of this version:", "", content.strip()]
    return "\n".join(lines)


def compose_eval_suite_doc(
    harness_title: str,
    asset_title: str,
    version_num: int,
    cases: list[dict],
) -> str:
    """Render the eval suite's cases as a study document.

    Each case dict carries: input, expected_output, grading_strategy.
    """
    lines = [
        f"Eval suite for harness \"{harness_title}\": {asset_title} (version {version_num})",
        "",
        f"The eval suite defines {len(cases)} test case(s) that the harness "
        "must pass. Each case sends an input to the composed prompt and grades "
        "the model's output with a grading strategy.",
    ]
    for i, case in enumerate(cases, start=1):
        lines += [
            "",
            f"Case {i} (graded by {case['grading_strategy']}): "
            f"given the input \"{case['input'].strip()}\", "
            f"the expected output is \"{case['expected_output'].strip()}\".",
        ]
    return "\n".join(lines)


def compose_eval_run_doc(
    harness_title: str,
    model_pin: str,
    provider: str,
    created_at: str,
    metrics: dict,
) -> str:
    """Render one completed eval run's metrics as a study document.

    metrics is the worker-written shape: {total, passed, failed, pass_rate,
    results: [{case_id, passed, actual_output, latency_ms, grading_strategy,
    error?}], usage?}.
    """
    total = metrics.get("total", 0)
    passed = metrics.get("passed", 0)
    failed = metrics.get("failed", 0)
    pass_rate = metrics.get("pass_rate", 0.0)

    lines = [
        f"Eval run report for harness \"{harness_title}\" — "
        f"model {model_pin} ({provider}), run at {created_at}",
        "",
        f"The run graded {total} case(s): {passed} passed and {failed} failed, "
        f"a pass rate of {round(pass_rate * 100, 1)}%.",
    ]

    usage = metrics.get("usage")
    if usage:
        lines += [
            "",
            f"Token usage: {usage.get('input_tokens', 0)} input tokens and "
            f"{usage.get('output_tokens', 0)} output tokens.",
        ]

    for i, result in enumerate(metrics.get("results") or [], start=1):
        verdict = "passed" if result.get("passed") else "FAILED"
        sentence = (
            f"Case {i} {verdict} "
            f"(graded by {result.get('grading_strategy', 'unknown')}, "
            f"{result.get('latency_ms', 0)}ms)."
        )
        if result.get("error"):
            sentence += f" Error: {result['error']}"
        elif not result.get("passed"):
            actual = (result.get("actual_output") or "")[:_ACTUAL_OUTPUT_EXCERPT]
            if actual:
                sentence += f" The model's actual output was: \"{actual}\""
        lines += ["", sentence]
    return "\n".join(lines)


def plan_study_projection(
    desired: list[tuple[str, str]],
    existing: dict[tuple[str, str], str],
) -> dict:
    """Decide what a create-or-refresh projection does (docs/12, OQ-33).

    desired: (doc_kind, ref_id) pairs in projection order — duplicates are
    dropped (two slots can reference the same asset version).
    existing: (doc_kind, ref_id) → the projected source's ingestion_status.

    Returns {"create": [...], "reenqueue": [...], "skipped": int}. Docs whose
    source previously failed are re-enqueued; docs that are pending, mid-
    ingest, or embedded are skipped (re-enqueueing an in-flight doc would
    race the worker for no benefit — chunk dedup makes it harmless but not
    useful).
    """
    create: list[tuple[str, str]] = []
    reenqueue: list[tuple[str, str]] = []
    skipped = 0
    seen: set[tuple[str, str]] = set()

    for key in desired:
        if key in seen:
            continue
        seen.add(key)
        status = existing.get(key)
        if status is None:
            create.append(key)
        elif status == "failed":
            reenqueue.append(key)
        else:
            skipped += 1

    return {"create": create, "reenqueue": reenqueue, "skipped": skipped}


def _humanize(role: str) -> str:
    return role.replace("_", " ")
