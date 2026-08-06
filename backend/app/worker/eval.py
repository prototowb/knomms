"""Eval job pipeline — runs eval suite cases against harness for an EvalRun record.

Called by the worker consumer for each eval.jobs message.
"""

import json
import logging
import re
import time
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.models  # noqa: F401 — ensures full ORM registry before any DB ops
from app.core.redis import get_redis
from app.models.asset import AssetVersion, EvalCase, EvalRun, Harness, HarnessAsset

logger = logging.getLogger(__name__)

_EVENTS_KEY_TTL = 3600  # keep progress events for 1 hour


def _normalize(text: str) -> str:
    """NFC + lowercase + collapse whitespace + strip leading/trailing punctuation."""
    text = unicodedata.normalize("NFC", text)
    # Normalize smart quotes to straight
    for bad, good in [("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'")]:
        text = text.replace(bad, good)
    text = text.lower()
    text = " ".join(text.split())
    text = text.strip(".,;:!?'\"-()[]{}/ \t")
    return text


def _grade(actual: str, expected: str, strategy: str, config: dict | None) -> bool:
    """Apply the grading strategy and return True if the case passes."""
    if strategy == "exact_match":
        return _normalize(actual) == _normalize(expected)
    if strategy == "contains":
        return _normalize(expected) in _normalize(actual)
    if strategy == "regex":
        pattern = (config or {}).get("pattern", expected)
        return bool(re.search(pattern, actual, re.IGNORECASE))
    if strategy == "llm_judge":
        # llm_judge is handled asynchronously in run_eval_job; this branch won't be reached
        return False
    return False


async def _generate(provider: str, prompt: str, model: str) -> tuple[str, dict | None]:
    """Provider dispatch (docs/11 OQ-23): returns (text, usage-or-None). The
    cloud adapter retries transient errors via the SDK; the local path gets a
    small retry of its own (OQ-27)."""
    if provider == "anthropic":
        from app.domains.generation import cloud

        return await cloud.generate(prompt, model)

    import asyncio

    import httpx

    from app.domains.generation.ollama import generate

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await generate(prompt, model=model), None
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            last_exc = exc
        await asyncio.sleep(2**attempt)
    raise last_exc  # type: ignore[misc]


async def _grade_llm(actual: str, expected: str, model: str, provider: str = "ollama") -> bool:
    """LLM judge — uses the run's own provider+model (judge == subject, OQ-28)."""
    prompt = (
        f"Does the following response correctly answer the question?\n\n"
        f"Expected: {expected}\n\nActual: {actual}\n\n"
        f"Reply with a single word: YES or NO."
    )
    result, _ = await _generate(provider, prompt, model)
    return "yes" in result.lower()


async def _push_event(redis, run_id: str, event: dict) -> None:
    key = f"eval:events:{run_id}"
    await redis.rpush(key, json.dumps(event))
    await redis.expire(key, _EVENTS_KEY_TTL)


async def run_eval_job(db: AsyncSession, job: dict) -> None:
    run_id: str = job["run_id"]

    eval_run = await db.get(EvalRun, run_id)
    if eval_run is None:
        logger.error("EvalRun %s not found — skipping job", run_id)
        return

    redis = await get_redis()

    try:
        eval_run.status = "running"
        await db.commit()

        # Load harness with asset slots
        harness = (
            await db.execute(
                select(Harness)
                .where(Harness.id == eval_run.harness_id)
                .options(selectinload(Harness.assets))
            )
        ).scalar_one_or_none()

        if harness is None:
            raise RuntimeError(f"Harness {eval_run.harness_id} not found")

        # Find eval_suite slot by role
        eval_suite_slot = next(
            (s for s in harness.assets if s.role == "eval_suite"), None
        )
        if eval_suite_slot is None:
            raise RuntimeError("Harness has no 'eval_suite' role slot")

        eval_suite_version = (
            await db.execute(
                select(AssetVersion)
                .where(AssetVersion.id == eval_suite_slot.asset_version_id)
                .options(selectinload(AssetVersion.eval_cases))
            )
        ).scalar_one_or_none()

        if eval_suite_version is None:
            raise RuntimeError("Eval suite asset version not found")

        # Snapshot which eval suite version this run used
        eval_run.eval_suite_version_id = eval_suite_version.id
        await db.commit()

        # Find system_prompt slot (optional)
        system_prompt_content: str | None = None
        sp_slot = next(
            (s for s in harness.assets if s.role == "system_prompt"), None
        )
        if sp_slot is not None:
            sp_version = await db.get(AssetVersion, sp_slot.asset_version_id)
            if sp_version is not None:
                system_prompt_content = sp_version.content

        cases: list[EvalCase] = eval_suite_version.eval_cases
        total = len(cases)
        model = eval_run.model_pin
        provider = eval_run.provider or "ollama"

        results = []
        passed_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for i, case in enumerate(cases):
            start_ms = int(time.monotonic() * 1000)

            # Build prompt
            if system_prompt_content:
                prompt = f"{system_prompt_content}\n\n{case.input}"
            else:
                prompt = case.input

            # One failed case must not fail the run (OQ-27) — capture the
            # error, count the case as failed, keep going
            error: str | None = None
            actual_output: str | None = None
            usage: dict | None = None
            passed = False
            try:
                actual_output, usage = await _generate(provider, prompt, model)
                if case.grading_strategy == "llm_judge":
                    passed = await _grade_llm(
                        actual_output, case.expected_output, model, provider
                    )
                else:
                    passed = _grade(
                        actual_output, case.expected_output,
                        case.grading_strategy, case.grading_config,
                    )
            except Exception as exc:
                logger.warning("EvalRun %s case %d errored: %s", run_id, i + 1, exc)
                error = str(exc)[:200]

            latency_ms = int(time.monotonic() * 1000) - start_ms

            if passed:
                passed_count += 1
            if usage:
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)

            result = {
                "case_id": case.id,
                "passed": passed,
                "actual_output": actual_output[:500] if actual_output else None,
                "latency_ms": latency_ms,
                "grading_strategy": case.grading_strategy,
            }
            if error:
                result["error"] = error
            if usage:
                result["usage"] = usage
            results.append(result)

            await _push_event(redis, run_id, {
                "type": "case",
                "case_num": i + 1,
                "total": total,
                "passed": passed,
                "latency_ms": latency_ms,
                **({"error": error} if error else {}),
            })

            logger.info(
                "EvalRun %s case %d/%d: %s (latency=%dms)",
                run_id, i + 1, total,
                "ERROR" if error else ("PASS" if passed else "FAIL"), latency_ms,
            )

        pass_rate = passed_count / total if total > 0 else 0.0
        metrics = {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "pass_rate": round(pass_rate, 4),
            "provider": provider,
            "results": results,
        }
        if provider == "anthropic":
            # Visible actuals after the bounded spend (OQ-25)
            metrics["usage"] = {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            }

        eval_run.metrics = metrics
        eval_run.status = "completed"
        await db.commit()

        await _push_event(redis, run_id, {
            "type": "complete",
            "metrics": {"total": total, "passed": passed_count, "pass_rate": round(pass_rate, 4)},
        })
        logger.info("EvalRun %s complete: %d/%d passed (%.0f%%)", run_id, passed_count, total, pass_rate * 100)

    except Exception:
        logger.exception("EvalRun %s failed", run_id)
        try:
            await db.rollback()
            eval_run.status = "failed"
            await db.commit()
            await _push_event(redis, run_id, {"type": "error", "message": "Eval job failed — check worker logs"})
        except Exception:
            logger.exception("Could not mark EvalRun %s as failed", run_id)
        raise
