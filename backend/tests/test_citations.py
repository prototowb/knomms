"""Unit tests for citation injection, validation, and SSE event formatting."""

import json

import pytest

from app.domains.generation.citations import (
    build_citations_dict,
    build_rag_prompt,
    citations_sse_event,
    extract_cited_ids,
    token_sse_event,
    validate_citations,
)
from app.domains.retrieval.types import RetrievedChunk

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _chunk(chunk_id: str, text: str = "Sample passage text.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_id="source-001",
        locator="page:1",
        text=text,
        score=0.1,
    )


CHUNK_A = _chunk("aaaaaaaa-0000-0000-0000-000000000001", "The sky is blue because of Rayleigh scattering.")
CHUNK_B = _chunk("bbbbbbbb-0000-0000-0000-000000000002", "Water boils at 100°C at sea level.")


# ── build_citations_dict ──────────────────────────────────────────────────────

def test_build_citations_dict_keys_are_chunk_ids():
    d = build_citations_dict([CHUNK_A, CHUNK_B])
    assert set(d.keys()) == {CHUNK_A.chunk_id, CHUNK_B.chunk_id}


def test_build_citations_dict_excerpt_truncated():
    long_chunk = _chunk("cccc-0001", "x" * 500)
    d = build_citations_dict([long_chunk])
    assert len(d[long_chunk.chunk_id]["excerpt"]) <= 200


def test_build_citations_dict_empty():
    assert build_citations_dict([]) == {}


# ── build_rag_prompt ──────────────────────────────────────────────────────────

def test_build_rag_prompt_contains_query():
    prompt = build_rag_prompt("Why is the sky blue?", [CHUNK_A])
    assert "Why is the sky blue?" in prompt


def test_build_rag_prompt_contains_chunk_id():
    prompt = build_rag_prompt("test", [CHUNK_A])
    assert CHUNK_A.chunk_id in prompt


def test_build_rag_prompt_contains_passage_text():
    prompt = build_rag_prompt("test", [CHUNK_A])
    assert "Rayleigh scattering" in prompt


def test_build_rag_prompt_instructs_citation():
    prompt = build_rag_prompt("test", [CHUNK_A])
    assert "[SOURCE:" in prompt  # instruction references the citation format


# ── extract_cited_ids ─────────────────────────────────────────────────────────

def test_extract_cited_ids_finds_citation():
    text = f"The sky is blue [SOURCE:{CHUNK_A.chunk_id}] due to scattering."
    ids = extract_cited_ids(text)
    assert CHUNK_A.chunk_id in ids


def test_extract_cited_ids_multiple():
    text = f"A [SOURCE:{CHUNK_A.chunk_id}] and B [SOURCE:{CHUNK_B.chunk_id}]."
    ids = extract_cited_ids(text)
    assert ids == {CHUNK_A.chunk_id, CHUNK_B.chunk_id}


def test_extract_cited_ids_none():
    assert extract_cited_ids("No citations here.") == set()


# ── validate_citations ────────────────────────────────────────────────────────

def test_validate_citations_clean():
    response = f"The sky is blue [SOURCE:{CHUNK_A.chunk_id}]."
    valid = {CHUNK_A.chunk_id}
    assert validate_citations(response, valid) == []


def test_validate_citations_detects_hallucination():
    fake_id = "ffffffff-0000-0000-0000-000000000099"
    response = f"The sky is blue [SOURCE:{fake_id}]."
    valid = {CHUNK_A.chunk_id}
    hallucinated = validate_citations(response, valid)
    assert fake_id in hallucinated


def test_validate_citations_empty_response():
    assert validate_citations("", {CHUNK_A.chunk_id}) == []


# ── SSE event format (must match useStreamingQuery.ts) ────────────────────────

def test_citations_sse_event_format():
    data = {"chunk-001": {"chunk_id": "chunk-001", "excerpt": "hello"}}
    event = citations_sse_event(data)
    # Must start with "event: citations\n"
    assert event.startswith("event: citations\n")
    # Must contain "data: " on a second line
    assert "\ndata: " in event
    # Must end with double newline (SSE separator)
    assert event.endswith("\n\n")
    # Data must be valid JSON matching input
    data_line = [l for l in event.split("\n") if l.startswith("data: ")][0]
    parsed = json.loads(data_line[len("data: "):])
    assert parsed == data


def test_token_sse_event_format():
    token = "hello"
    event = token_sse_event(token)
    # No "event:" field — frontend defaults eventType to 'message' and appends to response
    assert not event.startswith("event:")
    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    # Token content preserved exactly
    assert event == f"data: {token}\n\n"


def test_token_sse_event_special_chars():
    # Tokens with newlines or special chars must not break SSE parsing
    token = "line1\nline2"
    event = token_sse_event(token)
    assert event.startswith("data: ")
