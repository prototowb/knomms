"""Unit tests for the learning agent — pure logic, no DB or Ollama calls."""

import asyncio
import json

from app.domains.learning.agent import (
    _extract_heading,
    _fallback_title,
    _parse_json_response,
    build_concept_groups,
    generate_concept_proposal,
)
from app.domains.learning.types import PassageDraft


# ── _extract_heading ──────────────────────────────────────────────────────────


def test_extract_heading_finds_simple_prefix():
    text = "Introduction to Caching\n\nCaching is the process of storing..."
    assert _extract_heading(text) == "Introduction to Caching"


def test_extract_heading_finds_hierarchical_path():
    text = "Chapter 1 > Section 2 > Subsection A\n\nContent..."
    assert _extract_heading(text) == "Chapter 1 > Section 2 > Subsection A"


def test_extract_heading_ignores_long_prefix():
    long_prefix = "A" * 121
    text = f"{long_prefix}\n\nBody text here."
    assert _extract_heading(text) is None


def test_extract_heading_ignores_sentence_ending_prefix():
    text = "This is a complete sentence. With punctuation.\n\nBody text here."
    assert _extract_heading(text) is None


def test_extract_heading_ignores_question_mark():
    text = "Is this a question?\n\nYes it is."
    assert _extract_heading(text) is None


def test_extract_heading_no_double_newline():
    text = "No double newline here — just one paragraph."
    assert _extract_heading(text) is None


def test_extract_heading_empty_string():
    assert _extract_heading("") is None


# ── build_concept_groups ──────────────────────────────────────────────────────


def _chunk(id: str, source_id: str, locator: str, text: str, is_overlap: bool = False) -> dict:
    return {"id": id, "source_id": source_id, "locator": locator, "text": text, "is_overlap": is_overlap}


def test_build_concept_groups_same_heading_stays_together():
    chunks = [
        _chunk("c1", "s1", "p:1", "Introduction\n\nFirst paragraph."),
        _chunk("c2", "s1", "p:2", "Introduction\n\nSecond paragraph."),
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_build_concept_groups_splits_on_heading_change():
    chunks = [
        _chunk("c1", "s1", "p:1", "Chapter 1\n\nContent about chapter 1."),
        _chunk("c2", "s1", "p:2", "Chapter 2\n\nContent about chapter 2."),
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 2
    assert groups[0][0].chunk_id == "c1"
    assert groups[1][0].chunk_id == "c2"


def test_build_concept_groups_skips_overlap_chunks():
    chunks = [
        _chunk("c1", "s1", "p:1", "Intro\n\nFirst content."),
        _chunk("c2", "s1", "p:1", "Intro\n\nOverlap content.", is_overlap=True),
        _chunk("c3", "s1", "p:2", "Next Section\n\nNew content."),
    ]
    groups = build_concept_groups(chunks)
    all_ids = [p.chunk_id for g in groups for p in g]
    assert "c2" not in all_ids
    assert "c1" in all_ids
    assert "c3" in all_ids


def test_build_concept_groups_no_heading_groups_together():
    chunks = [
        _chunk("c1", "s1", "p:1", "Plain sentence without a heading prefix."),
        _chunk("c2", "s1", "p:2", "Another plain sentence without a heading."),
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_build_concept_groups_empty_input():
    assert build_concept_groups([]) == []


def test_build_concept_groups_all_overlap_yields_nothing():
    chunks = [
        _chunk("c1", "s1", "p:1", "Content.", is_overlap=True),
        _chunk("c2", "s1", "p:2", "Content.", is_overlap=True),
    ]
    assert build_concept_groups(chunks) == []


def test_build_concept_groups_passage_fields():
    chunks = [_chunk("abc", "src1", "page:5", "Section A\n\nContent.")]
    groups = build_concept_groups(chunks)
    p = groups[0][0]
    assert p.chunk_id == "abc"
    assert p.source_id == "src1"
    assert p.locator == "page:5"


# ── build_concept_groups — KC-074 (source boundary + cap, realistic chunker output) ──
#
# Real chunker output NEVER contains "\n\n" (windows are rejoined with single
# spaces — chunker.py _build_windows), so these tests use newline-free text.
# Before KC-074 every such KB collapsed into exactly one concept group.


def test_build_concept_groups_splits_on_source_boundary_without_headings():
    chunks = [
        _chunk("c1", "s1", "para:1", "Chapter 1 > Intro Caching stores hot data. It reduces latency."),
        _chunk("c2", "s1", "para:2", "Eviction policies decide what to drop when the cache is full."),
        _chunk("c3", "s2", "para:1", "Write-ahead logging ensures durability before commits are acknowledged."),
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 2
    assert [p.chunk_id for p in groups[0]] == ["c1", "c2"]
    assert [p.chunk_id for p in groups[1]] == ["c3"]


def test_build_concept_groups_one_group_per_source_for_many_sources():
    chunks = [
        _chunk(f"c{i}", f"s{i}", "para:1", f"Facet document {i} body text with no headings.")
        for i in range(5)
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 5


def test_build_concept_groups_caps_group_size():
    chunks = [
        _chunk(f"c{i}", "s1", f"para:{i}", f"Plain passage number {i} without any heading.")
        for i in range(10)
    ]
    groups = build_concept_groups(chunks)
    assert [len(g) for g in groups] == [8, 2]


def test_build_concept_groups_overlap_chunks_do_not_count_toward_cap():
    chunks = []
    for i in range(8):
        chunks.append(_chunk(f"c{i}", "s1", f"para:{i}", f"Passage {i}."))
        chunks.append(_chunk(f"o{i}", "s1", f"para:{i}", f"Overlap {i}.", is_overlap=True))
    groups = build_concept_groups(chunks)
    assert len(groups) == 1
    assert len(groups[0]) == 8


def test_build_concept_groups_source_boundary_splits_even_with_same_heading():
    chunks = [
        _chunk("c1", "s1", "p:1", "Intro\n\nSource one content."),
        _chunk("c2", "s2", "p:1", "Intro\n\nSource two content."),
    ]
    groups = build_concept_groups(chunks)
    assert len(groups) == 2


# ── _parse_json_response ──────────────────────────────────────────────────────


def test_parse_json_clean_object():
    raw = '{"title": "Test", "explanation": "Some text."}'
    result = _parse_json_response(raw)
    assert result is not None
    assert result["title"] == "Test"


def test_parse_json_strips_markdown_fence():
    raw = "```json\n{\"title\": \"Fenced\"}\n```"
    result = _parse_json_response(raw)
    assert result is not None
    assert result["title"] == "Fenced"


def test_parse_json_extracts_embedded_object():
    raw = 'Here is the result:\n{"title": "Embedded"}\nDone.'
    result = _parse_json_response(raw)
    assert result is not None
    assert result["title"] == "Embedded"


def test_parse_json_invalid_returns_none():
    assert _parse_json_response("This is not JSON at all.") is None


def test_parse_json_empty_string_returns_none():
    assert _parse_json_response("") is None


# ── _fallback_title ───────────────────────────────────────────────────────────


def test_fallback_title_uses_heading():
    group = [PassageDraft("c1", "p:1", "s1", "Section 3\n\nContent here.")]
    assert _fallback_title(group) == "Section 3"


def test_fallback_title_uses_locator_when_no_heading():
    group = [PassageDraft("c1", "p:5", "s1", "No double newline — plain text.")]
    assert _fallback_title(group) == "Concept from p:5"


def test_fallback_title_empty_group():
    assert _fallback_title([]) == "Unknown concept"


# ── generate_concept_proposal ─────────────────────────────────────────────────


def test_generate_concept_proposal_success(monkeypatch):
    group = [
        PassageDraft(
            "abc-123", "p:1", "s1", "Write-ahead logging\n\nWAL ensures durability."
        )
    ]
    mock_resp = json.dumps({
        "title": "Write-ahead logging",
        "explanation": "WAL ensures durability [SOURCE:abc-123].",
        "passage_ids_cited": ["abc-123"],
        "question": {
            "question_text": "What does WAL ensure?",
            "correct_answer": "Durability",
            "grounding_passage_id": "abc-123",
            "distractors": [
                {
                    "text": "Compression",
                    "why_wrong_passage_id": "abc-123",
                    "misconception_label": "confuses WAL with compression",
                }
            ],
        },
    })

    async def _mock_generate(prompt: str) -> str:
        return mock_resp

    monkeypatch.setattr("app.domains.learning.agent._ollama_generate", _mock_generate)

    proposal = asyncio.run(generate_concept_proposal(group))
    assert proposal is not None
    assert proposal.title == "Write-ahead logging"
    assert "abc-123" in proposal.passage_ids_cited
    assert proposal.assessment is not None
    assert proposal.assessment.correct_answer == "Durability"
    assert len(proposal.assessment.distractors) == 1
    assert proposal.assessment.distractors[0].misconception_label == "confuses WAL with compression"


def test_generate_concept_proposal_hallucinated_citation_discarded(monkeypatch):
    group = [PassageDraft("real-id", "p:1", "s1", "Some content.")]
    mock_resp = json.dumps({
        "title": "Test",
        "explanation": "Content [SOURCE:fake-id].",
        "passage_ids_cited": ["fake-id"],
        "question": {
            "question_text": "Q?",
            "correct_answer": "A",
            "grounding_passage_id": "fake-id",
            "distractors": [],
        },
    })

    async def _mock_generate(prompt: str) -> str:
        return mock_resp

    monkeypatch.setattr("app.domains.learning.agent._ollama_generate", _mock_generate)
    assert asyncio.run(generate_concept_proposal(group)) is None


def test_generate_concept_proposal_unparseable_response(monkeypatch):
    group = [PassageDraft("c1", "p:1", "s1", "Content.")]

    async def _mock_generate(prompt: str) -> str:
        return "I cannot generate that content."

    monkeypatch.setattr("app.domains.learning.agent._ollama_generate", _mock_generate)
    assert asyncio.run(generate_concept_proposal(group)) is None


def test_generate_concept_proposal_no_assessment_when_grounding_invalid(monkeypatch):
    """Assessment is skipped if grounding_passage_id is not in the passage set."""
    group = [PassageDraft("valid-id", "p:1", "s1", "Real content.")]
    mock_resp = json.dumps({
        "title": "Concept",
        "explanation": "Some explanation [SOURCE:valid-id].",
        "passage_ids_cited": ["valid-id"],
        "question": {
            "question_text": "Q?",
            "correct_answer": "A",
            "grounding_passage_id": "not-in-group",  # invalid — grounding drops the assessment
            "distractors": [],
        },
    })

    async def _mock_generate(prompt: str) -> str:
        return mock_resp

    monkeypatch.setattr("app.domains.learning.agent._ollama_generate", _mock_generate)

    proposal = asyncio.run(generate_concept_proposal(group))
    assert proposal is not None
    assert proposal.title == "Concept"
    assert proposal.assessment is None
