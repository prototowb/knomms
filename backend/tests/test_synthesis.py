"""Unit tests for multi-source synthesis prompt + guards — pure logic, no DB (KC-096)."""

from app.domains.generation.synthesis import (
    MAX_SOURCES,
    MIN_SOURCES,
    build_synthesis_prompt,
    check_source_selection,
)
from app.domains.retrieval.types import RetrievedChunk


def _chunk(cid: str, sid: str, text: str = "some passage text") -> RetrievedChunk:
    return RetrievedChunk(chunk_id=cid, source_id=sid, locator="para:1", text=text, score=0.1)


# ── check_source_selection ────────────────────────────────────────────────────


def test_valid_selection():
    assert check_source_selection(["a", "b"], {"a", "b", "c"}) is None
    assert check_source_selection(["a", "b", "c", "d", "e"], set("abcde")) is None


def test_too_few_or_too_many():
    assert "between" in check_source_selection(["a"], {"a", "b"})
    assert "between" in check_source_selection(list("abcdef"), set("abcdef"))
    assert MIN_SOURCES == 2 and MAX_SOURCES == 5


def test_foreign_source_rejected():
    assert "belong" in check_source_selection(["a", "zz"], {"a", "b"})


def test_duplicates_rejected():
    assert "duplicates" in check_source_selection(["a", "a"], {"a", "b"})


# ── build_synthesis_prompt ────────────────────────────────────────────────────


def test_groups_render_with_source_headers():
    prompt = build_synthesis_prompt(
        "How do they differ?",
        [
            ("Paper One", [_chunk("c1", "s1"), _chunk("c2", "s1")]),
            ("Talk Two", [_chunk("c3", "s2")]),
        ],
    )
    assert "--- SOURCE: Paper One ---" in prompt
    assert "--- SOURCE: Talk Two ---" in prompt
    assert prompt.index("Paper One") < prompt.index("Talk Two")  # selection order kept
    assert "chunk_id=c1" in prompt and "chunk_id=c3" in prompt
    assert "[SOURCE:chunk_id]" in prompt  # citation instruction
    assert "QUESTION: How do they differ?" in prompt
    assert prompt.rstrip().endswith("COMPARISON:")


def test_empty_group_reported_not_dropped():
    prompt = build_synthesis_prompt(
        "q?",
        [("Has Content", [_chunk("c1", "s1")]), ("Empty Source", [])],
    )
    assert "--- SOURCE: Empty Source ---" in prompt
    assert "no relevant passages found" in prompt


def test_comparison_instructions_present():
    prompt = build_synthesis_prompt("q?", [("A", [_chunk("c1", "s1")]), ("B", [_chunk("c2", "s2")])])
    assert "agree" in prompt and "disagree" in prompt
    assert "never invent" in prompt
