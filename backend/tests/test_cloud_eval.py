"""Unit tests for the cloud eval adapter plumbing (docs/11-cloud-eval-adapter.md)."""

from types import SimpleNamespace

from app.core.config import settings
from app.domains.generation.cloud import extract_text, is_enabled
from app.domains.harnesses.service import EVAL_PROVIDERS

# ── opt-in gate (OQ-21) ──────────────────────────────────────────────────────


def _with_settings(enabled, key):
    old = (settings.cloud_eval_enabled, settings.anthropic_api_key)
    settings.cloud_eval_enabled, settings.anthropic_api_key = enabled, key
    try:
        return is_enabled()
    finally:
        settings.cloud_eval_enabled, settings.anthropic_api_key = old


def test_disabled_by_default() -> None:
    # The shipped defaults must keep every cloud path unreachable (OQ-2)
    assert settings.__class__().cloud_eval_enabled is False
    assert settings.__class__().anthropic_api_key is None


def test_enabled_requires_both_flag_and_key() -> None:
    assert _with_settings(False, None) is False
    assert _with_settings(True, None) is False
    assert _with_settings(False, "sk-ant-x") is False
    assert _with_settings(True, "sk-ant-x") is True


def test_empty_key_does_not_enable() -> None:
    assert _with_settings(True, "") is False


# ── provider vocabulary (OQ-22) ──────────────────────────────────────────────


def test_eval_providers_vocabulary() -> None:
    assert EVAL_PROVIDERS == {"ollama", "anthropic"}


def test_guardrail_defaults() -> None:
    fresh = settings.__class__()
    assert fresh.cloud_eval_max_cases == 25
    assert fresh.cloud_eval_max_tokens == 4096


# ── response text extraction ─────────────────────────────────────────────────


def _block(type_: str, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(type=type_, text=text)


def test_extract_text_concatenates_text_blocks() -> None:
    content = [_block("text", "Hello "), _block("text", "world")]
    assert extract_text(content) == "Hello world"


def test_extract_text_skips_non_text_blocks() -> None:
    # thinking blocks precede text on current models — never index content[0]
    content = [_block("thinking"), _block("text", "answer")]
    assert extract_text(content) == "answer"


def test_extract_text_empty_content() -> None:
    assert extract_text([]) == ""
