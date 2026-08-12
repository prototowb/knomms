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


# ── compose_synthesis_doc (KC-100, docs/17 OQ-72) ─────────────────────────────


def test_compose_doc_shape():
    from app.domains.generation.synthesis import compose_synthesis_doc

    doc = compose_synthesis_doc(
        "How do they differ?",
        "They differ a lot.",
        [
            {"chunk_id": "c1", "source_id": "s1", "locator": "para:3", "excerpt": "x"},
            {"chunk_id": "c2", "source_id": "s2", "locator": "ts:00:01:33", "excerpt": "y"},
            {"chunk_id": "c3", "source_id": "s1", "locator": "para:9", "excerpt": "z"},
        ],
        {"s1": "Paper One", "s2": "Talk Two"},
    )
    assert doc.startswith("# How do they differ?")
    assert "They differ a lot." in doc
    assert "- Paper One: para:3, para:9" in doc
    assert "- Talk Two: ts:00:01:33" in doc


def test_compose_doc_without_citations():
    from app.domains.generation.synthesis import compose_synthesis_doc

    doc = compose_synthesis_doc("q?", "answer", [], {})
    assert "(no citations recorded)" in doc


def test_compose_doc_unknown_source_falls_back_to_id():
    from app.domains.generation.synthesis import compose_synthesis_doc

    doc = compose_synthesis_doc(
        "q?", "a",
        [{"chunk_id": "c1", "source_id": "sX", "locator": "para:1", "excerpt": "x"}],
        {},
    )
    assert "- sX: para:1" in doc


# ── SaveSynthesisRequest caps (KC-099, docs/17 OQ-70) ─────────────────────────


def test_save_request_caps():
    import pytest
    from pydantic import ValidationError

    from app.schemas.synthesis import MAX_ANSWER_CHARS, SaveSynthesisRequest

    ok = SaveSynthesisRequest(question="q", answer_text="a", source_ids=["s1", "s2"])
    assert ok.citations == []

    with pytest.raises(ValidationError):
        SaveSynthesisRequest(question="q", answer_text="", source_ids=["s1", "s2"])
    with pytest.raises(ValidationError):
        SaveSynthesisRequest(
            question="q", answer_text="a" * (MAX_ANSWER_CHARS + 1), source_ids=["s1", "s2"]
        )
    with pytest.raises(ValidationError):
        SaveSynthesisRequest(
            question="q",
            answer_text="a",
            source_ids=["s1"],
            citations=[
                {"chunk_id": "c", "source_id": "s", "locator": "l", "excerpt": "e"}
            ] * 51,
        )
