"""Semantic chunker: RawBlock[] → Chunk-shaped dicts ready for DB insert.

Strategy:
1. Group consecutive BODY/CAPTION blocks within the same heading section.
2. Split sections at ~400 tokens; merge sections < 80 tokens with their successor.
3. Apply 20% token overlap between adjacent chunks within a section.
4. HEADING blocks are NOT chunked themselves — their text is injected as a
   heading_path prefix into the first BODY chunk of their section.

This module is pure (no I/O, no DB). All logic is unit-testable.
"""

import hashlib
import re
import uuid

_APPROX_TOKENS_PER_CHAR = 0.25  # rough: 1 token ≈ 4 chars for English

TARGET_TOKENS = 400
MIN_TOKENS = 80
OVERLAP_RATIO = 0.20


def _approx_tokens(text: str) -> int:
    return max(1, int(len(text) * _APPROX_TOKENS_PER_CHAR))


def chunk_blocks(
    blocks: list,  # list[RawBlock]
    source_id: str,
    vector_namespace: str,
) -> list[dict]:
    """
    Returns a list of dicts matching the Chunk ORM model fields:
      id, source_id, seq, locator, text, vector_namespace,
      content_hash, is_overlap, embedding_model_id (None — set after embedding)
    """
    if not blocks:
        return []

    # 1. Split into heading-sections
    sections = _split_into_sections(blocks)

    chunks: list[dict] = []
    seq = 0

    for section_blocks in sections:
        # Concatenate all BODY/CAPTION text in the section
        body_blocks = [b for b in section_blocks if b.block_type in ("BODY", "CAPTION")]
        if not body_blocks:
            continue

        heading_prefix = ""
        if section_blocks[0].heading_path:
            heading_prefix = " > ".join(section_blocks[0].heading_path) + "\n\n"

        full_text = heading_prefix + "\n\n".join(b.text for b in body_blocks)
        locator = body_blocks[0].page_or_position

        # 2. Split the concatenated text into target-size windows
        sentences = _split_sentences(full_text)
        windows = _build_windows(sentences)

        for i, (window_text, is_overlap) in enumerate(windows):
            chunk_text = window_text.strip()
            if not chunk_text:
                continue

            chunks.append({
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "seq": seq,
                "locator": locator,
                "text": chunk_text,
                "vector_namespace": vector_namespace,
                "content_hash": _content_hash(chunk_text),
                "is_overlap": is_overlap,
                "embedding_model_id": None,
            })
            seq += 1

    return chunks


def _split_into_sections(blocks: list) -> list[list]:
    """Group blocks by heading boundary — a new HEADING starts a new section."""
    sections: list[list] = []
    current: list = []

    for block in blocks:
        if block.block_type == "HEADING":
            if current:
                sections.append(current)
            current = [block]
        else:
            current.append(block)

    if current:
        sections.append(current)

    return sections


def _split_sentences(text: str) -> list[str]:
    """Crude sentence splitter — split on '. ', '! ', '? ' and newlines."""
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    return [p.strip() for p in parts if p.strip()]


def _build_windows(sentences: list[str]) -> list[tuple[str, bool]]:
    """Build (text, is_overlap) windows from a sentence list.

    Each window aims for TARGET_TOKENS. The overlap region (the last
    OVERLAP_RATIO of the previous window's sentences) is prepended to
    the next window with is_overlap=True on that chunk.
    """
    if not sentences:
        return []

    windows: list[tuple[str, bool]] = []
    i = 0

    while i < len(sentences):
        window_sentences: list[str] = []
        token_count = 0

        # Overlap from previous window
        overlap_sentences: list[str] = []
        if windows:
            prev_text = windows[-1][0]
            prev_sents = _split_sentences(prev_text)
            overlap_count = max(1, int(len(prev_sents) * OVERLAP_RATIO))
            overlap_sentences = prev_sents[-overlap_count:]

        j = i
        while j < len(sentences):
            candidate = sentences[j]
            candidate_tokens = _approx_tokens(candidate)
            if token_count + candidate_tokens > TARGET_TOKENS and window_sentences:
                break
            window_sentences.append(candidate)
            token_count += candidate_tokens
            j += 1

        if not window_sentences:
            # Single sentence longer than TARGET — include it anyway
            window_sentences = [sentences[i]]
            j = i + 1

        # Merge short trailing window into previous
        if _approx_tokens(" ".join(window_sentences)) < MIN_TOKENS and windows:
            prev_text, prev_overlap = windows[-1]
            merged = prev_text + " " + " ".join(window_sentences)
            windows[-1] = (merged, prev_overlap)
            i = j
            continue

        is_overlap = bool(overlap_sentences)
        window_text = " ".join(overlap_sentences + window_sentences) if overlap_sentences else " ".join(window_sentences)
        windows.append((window_text, is_overlap))
        i = j

    return windows


def _content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:64]
