"""Anthropic cloud eval adapter (docs/11-cloud-eval-adapter.md, OQ-21–28).

Reachable ONLY from the eval path, and only when the operator has opted in
(CLOUD_EVAL_ENABLED=true + ANTHROPIC_API_KEY). With the defaults, no request
ever leaves the host — the zero-external-cost invariant (OQ-2) holds.
"""

from app.core.config import settings


class CloudGenerationError(RuntimeError):
    """A cloud generation attempt failed for one eval case."""


_client = None


def is_enabled() -> bool:
    return bool(settings.cloud_eval_enabled and settings.anthropic_api_key)


def _get_client():
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        # max_retries=3 → SDK exponential backoff on 429/5xx/connection errors
        # (OQ-27); one failed case must not fail the run — the worker catches
        # per case on top of this.
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=3)
    return _client


def extract_text(content) -> str:
    """Concatenate the text blocks of a Messages API response. Content is a
    list of typed blocks (text, thinking, ...) — never index blindly."""
    return "".join(block.text for block in content if block.type == "text")


async def list_models() -> list[str]:
    """Live model list from the provider's Models API — no hardcoded ids (OQ-23)."""
    client = _get_client()
    return [m.id async for m in client.models.list()]


async def generate(prompt: str, model: str) -> tuple[str, dict[str, int]]:
    """One eval-case completion. Returns (text, usage token counts) — token
    counts feed the run metrics (OQ-25)."""
    client = _get_client()
    resp = await client.messages.create(
        model=model,
        max_tokens=settings.cloud_eval_max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    # A refusal is HTTP 200 with stop_reason set — check before reading content
    if resp.stop_reason == "refusal":
        raise CloudGenerationError("Provider declined the request (safety refusal)")
    usage = {
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }
    return extract_text(resp.content), usage
