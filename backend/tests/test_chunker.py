"""Unit tests for the semantic chunker — pure logic, no I/O."""

import pytest

from app.domains.ingestion.blocks import RawBlock
from app.domains.ingestion.chunker import (
    _approx_tokens,
    _build_windows,
    _content_hash,
    _split_into_sections,
    _split_sentences,
    chunk_blocks,
)

SOURCE_ID = "test-source-001"
NAMESPACE = "kb:test-001"


# ── _split_into_sections ──────────────────────────────────────────────────────

def _block(text: str, block_type: str = "BODY", idx: int = 0) -> RawBlock:
    return RawBlock(text=text, source_id=SOURCE_ID, block_index=idx, page_or_position=f"page:{idx+1}", block_type=block_type)


def test_split_sections_no_headings():
    blocks = [_block("A"), _block("B"), _block("C")]
    sections = _split_into_sections(blocks)
    assert len(sections) == 1
    assert len(sections[0]) == 3


def test_split_sections_heading_starts_new_section():
    blocks = [
        _block("Intro", "BODY"),
        _block("Section 1", "HEADING"),
        _block("Body 1", "BODY"),
        _block("Section 2", "HEADING"),
        _block("Body 2", "BODY"),
    ]
    sections = _split_into_sections(blocks)
    assert len(sections) == 3
    assert sections[0][0].text == "Intro"
    assert sections[1][0].block_type == "HEADING"
    assert sections[2][0].block_type == "HEADING"


# ── _build_windows ────────────────────────────────────────────────────────────

def test_build_windows_single_sentence():
    sentences = ["Hello world."]
    windows = _build_windows(sentences)
    assert len(windows) == 1
    assert "Hello world." in windows[0][0]
    assert windows[0][1] is False  # first window has no overlap


def test_build_windows_overlap_on_second_window():
    # Sentences must be long enough that 30 of them exceed the 400-token target.
    # Each sentence: "word " * 40 ≈ 200 chars ≈ 50 tokens → 30 sentences ≈ 1500 tokens
    long_sentence = "word " * 40
    sentences = [long_sentence.strip() for _ in range(30)]
    windows = _build_windows(sentences)
    assert len(windows) >= 2, f"Expected multiple windows, got {len(windows)}"
    # Second window should be flagged as containing overlap content
    assert windows[1][1] is True


def test_build_windows_respects_target_tokens():
    # Use realistic sentences WITH punctuation so _split_sentences can split the
    # overlap region correctly. Each sentence ≈ 30 tokens.
    sentence = "The quick brown fox jumps over the lazy dog near the riverbank every morning. "
    sentences = [sentence.strip() for _ in range(30)]
    windows = _build_windows(sentences)
    assert len(windows) >= 2, "Expected multiple windows for 30 sentences"
    for window_text, _ in windows:
        tokens = _approx_tokens(window_text)
        # Each window should stay well under 3× TARGET even with overlap
        assert tokens < 1200, f"Window too large: {tokens} tokens"


# ── chunk_blocks ──────────────────────────────────────────────────────────────

def test_chunk_blocks_empty():
    assert chunk_blocks([], SOURCE_ID, NAMESPACE) == []


def test_chunk_blocks_basic_structure():
    blocks = [_block("Hello " * 100, "BODY")]  # ~600 chars ≈ 150 tokens — well under limit
    chunks = chunk_blocks(blocks, SOURCE_ID, NAMESPACE)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["source_id"] == SOURCE_ID
        assert c["vector_namespace"] == NAMESPACE
        assert c["embedding_model_id"] is None
        assert len(c["content_hash"]) == 64
        assert c["text"]


def test_chunk_blocks_heading_prefix_injected():
    blocks = [
        RawBlock(
            text="Introduction",
            source_id=SOURCE_ID,
            block_index=0,
            page_or_position="page:1",
            block_type="HEADING",
            heading_path=["Chapter 1"],
        ),
        RawBlock(
            text="This chapter covers the basics of knowledge management systems.",
            source_id=SOURCE_ID,
            block_index=1,
            page_or_position="page:1",
            block_type="BODY",
            heading_path=["Chapter 1"],
        ),
    ]
    chunks = chunk_blocks(blocks, SOURCE_ID, NAMESPACE)
    assert chunks
    # The heading path should be reflected in the chunk text
    assert "Chapter 1" in chunks[0]["text"]


def test_chunk_blocks_seq_is_monotonic():
    blocks = [_block(f"Paragraph {i}. " * 20, idx=i) for i in range(5)]
    chunks = chunk_blocks(blocks, SOURCE_ID, NAMESPACE)
    seqs = [c["seq"] for c in chunks]
    assert seqs == list(range(len(chunks)))


# ── _content_hash ─────────────────────────────────────────────────────────────

def test_content_hash_deterministic():
    assert _content_hash("hello world") == _content_hash("hello world")


def test_content_hash_normalizes_whitespace():
    assert _content_hash("hello   world") == _content_hash("hello world")
    assert _content_hash("hello\nworld") == _content_hash("hello world")


def test_content_hash_case_insensitive():
    assert _content_hash("Hello World") == _content_hash("hello world")


def test_content_hash_different_texts_differ():
    assert _content_hash("apple") != _content_hash("orange")
