"""Unit tests for YouTube URL parsing, transcript preference, and block building — pure logic (KC-092)."""

from dataclasses import dataclass

from app.domains.ingestion.extractors.video import (
    MAX_BLOCK_CHARS,
    build_transcript_blocks,
    format_timestamp,
    parse_video_url,
    pick_transcript,
)

VID = "jNQXAC9IVRw"


# ── parse_video_url ───────────────────────────────────────────────────────────


def test_watch_url_forms():
    assert parse_video_url(f"https://www.youtube.com/watch?v={VID}") == VID
    assert parse_video_url(f"https://youtube.com/watch?v={VID}&t=42s") == VID
    assert parse_video_url(f"https://m.youtube.com/watch?v={VID}") == VID


def test_short_and_path_forms():
    assert parse_video_url(f"https://youtu.be/{VID}") == VID
    assert parse_video_url(f"https://youtu.be/{VID}?t=30") == VID
    assert parse_video_url(f"https://www.youtube.com/shorts/{VID}") == VID
    assert parse_video_url(f"https://www.youtube.com/embed/{VID}") == VID
    assert parse_video_url(f"https://www.youtube.com/live/{VID}") == VID
    assert parse_video_url(f"https://www.youtube-nocookie.com/embed/{VID}") == VID


def test_non_video_urls_rejected():
    assert parse_video_url("https://en.wikipedia.org/wiki/YouTube") is None
    assert parse_video_url("https://www.youtube.com/@somechannel") is None
    assert parse_video_url("https://www.youtube.com/playlist?list=PL123abc") is None
    assert parse_video_url("https://www.youtube.com/watch?list=PL123abc") is None
    assert parse_video_url("https://youtube.com/watch?v=too-short") is None
    assert parse_video_url("https://notyoutube.com/watch?v=" + VID) is None
    assert parse_video_url("https://fakeyoutube.com/watch?v=" + VID) is None


# ── format_timestamp ──────────────────────────────────────────────────────────


def test_timestamp_format():
    assert format_timestamp(0) == "ts:00:00:00"
    assert format_timestamp(93.7) == "ts:00:01:33"
    assert format_timestamp(3661) == "ts:01:01:01"


# ── build_transcript_blocks ───────────────────────────────────────────────────


def _snips(*pairs):
    return [{"text": t, "start": s} for s, t in pairs]


def test_snippets_accumulate_into_one_block():
    blocks = build_transcript_blocks(
        _snips((1.2, "All right, so here we are"), (5.3, "in front of the elephants")), "s1"
    )
    assert len(blocks) == 1
    assert blocks[0].text == "All right, so here we are in front of the elephants"
    assert blocks[0].page_or_position == "ts:00:00:01"
    assert blocks[0].block_index == 0


def test_block_closes_at_char_cap_and_locator_tracks_first_snippet():
    long_word = "x" * 90
    snippets = _snips(*[(float(i * 10), long_word) for i in range(10)])
    blocks = build_transcript_blocks(snippets, "s1")
    assert len(blocks) > 1
    assert all(len(b.text) <= MAX_BLOCK_CHARS + 91 for b in blocks)
    assert blocks[0].page_or_position == "ts:00:00:00"
    # Second block starts at the first snippet not in block 1
    per_block = MAX_BLOCK_CHARS // 91 + 1
    assert blocks[1].page_or_position == format_timestamp(per_block * 10)
    assert [b.block_index for b in blocks] == list(range(len(blocks)))


def test_sentence_end_closes_block_after_half_cap():
    filler = "y" * (MAX_BLOCK_CHARS // 2)
    blocks = build_transcript_blocks(
        _snips((0, filler), (10, "And that is the point."), (20, "Next topic begins")), "s1"
    )
    assert len(blocks) == 2
    assert blocks[0].text.endswith("the point.")
    assert blocks[1].text == "Next topic begins"
    assert blocks[1].page_or_position == "ts:00:00:20"


def test_whitespace_snippets_skipped_and_newlines_collapsed():
    blocks = build_transcript_blocks(
        _snips((0, "line one\nline two"), (2, "   "), (4, "tail")), "s1"
    )
    assert len(blocks) == 1
    assert blocks[0].text == "line one line two tail"


def test_empty_input():
    assert build_transcript_blocks([], "s1") == []


# ── pick_transcript ───────────────────────────────────────────────────────────


@dataclass
class _T:
    language_code: str
    is_generated: bool


def test_manual_english_wins():
    picked = pick_transcript([_T("de", False), _T("en", True), _T("en", False)])
    assert (picked.language_code, picked.is_generated) == ("en", False)


def test_manual_any_beats_generated_english():
    picked = pick_transcript([_T("en", True), _T("de", False)])
    assert (picked.language_code, picked.is_generated) == ("de", False)


def test_generated_english_beats_generated_other():
    picked = pick_transcript([_T("fr", True), _T("en-US", True)])
    assert picked.language_code == "en-US"


def test_no_transcripts():
    assert pick_transcript([]) is None
