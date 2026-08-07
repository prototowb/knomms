"""YouTube transcript extractor (docs/15, OQ-53–59).

Ingests the captions a video already has — no ASR (that is part 2). The
transcript client is synchronous, so the fetch runs via asyncio.to_thread;
everything else here is pure and unit-tested (URL parsing, transcript
preference, block accumulation).
"""

import asyncio
import re
from urllib.parse import parse_qs, urlparse

from app.domains.ingestion.blocks import RawBlock
from app.domains.ingestion.extractors.base import BaseExtractor

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_FORMS = ("embed", "shorts", "live", "v")

# Blocks accumulate snippets to roughly prose-paragraph size (OQ-56) — raw
# caption snippets are 2–8 words, far too small to embed or cite.
MAX_BLOCK_CHARS = 400
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?$")


def parse_video_url(url: str) -> str | None:
    """Video id for a YouTube URL, else None (OQ-53/55). Pure.

    Handles watch?v=, youtu.be/, and the embed/shorts/live/v path forms.
    Playlist pages without a video id are not videos.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host not in ("youtube.com", "youtube-nocookie.com", "youtu.be"):
        return None

    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    else:
        segments = [s for s in parsed.path.split("/") if s]
        if parsed.path == "/watch" or parsed.path == "/watch/":
            candidate = (parse_qs(parsed.query).get("v") or [None])[0]
        elif len(segments) >= 2 and segments[0] in _PATH_FORMS:
            candidate = segments[1]

    if candidate and _VIDEO_ID_RE.match(candidate):
        return candidate
    return None


def format_timestamp(seconds: float) -> str:
    """ts:HH:MM:SS — the RawBlock locator convention for time-based media."""
    total = int(seconds)
    return f"ts:{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def build_transcript_blocks(snippets: list[dict], source_id: str) -> list[RawBlock]:
    """Accumulate caption snippets into ~MAX_BLOCK_CHARS blocks (OQ-56). Pure.

    A block closes early on a sentence end once past half the cap, so block
    boundaries land on natural pauses where the captions allow it. The
    locator is the start time of the block's first snippet.
    """
    blocks: list[RawBlock] = []
    parts: list[str] = []
    chars = 0
    start: float = 0.0

    def _flush() -> None:
        nonlocal parts, chars
        text = " ".join(parts).strip()
        if text:
            blocks.append(
                RawBlock(
                    text=text,
                    source_id=source_id,
                    block_index=len(blocks),
                    page_or_position=format_timestamp(start),
                )
            )
        parts, chars = [], 0

    for snippet in snippets:
        text = " ".join((snippet.get("text") or "").split())
        if not text:
            continue
        if not parts:
            start = float(snippet.get("start") or 0.0)
        parts.append(text)
        chars += len(text) + 1
        if chars >= MAX_BLOCK_CHARS or (
            chars >= MAX_BLOCK_CHARS // 2 and _SENTENCE_END_RE.search(text)
        ):
            _flush()
    _flush()
    return blocks


def pick_transcript(transcripts) -> object | None:
    """Preference order (OQ-57): manual English > manual any > generated
    English > generated any. Pure — items need .language_code/.is_generated."""
    ranked = sorted(
        transcripts,
        key=lambda t: (
            t.is_generated,
            not t.language_code.lower().startswith("en"),
        ),
    )
    return ranked[0] if ranked else None


class VideoExtractor(BaseExtractor):
    """Fetches the transcript itself (OQ-58) — `extract` from bytes is not a
    meaningful operation for a video URL source."""

    async def extract(self, content: bytes, source_id: str, url: str | None = None) -> list[RawBlock]:
        if url is None:
            raise ValueError("Video sources require a URL")
        return await self.fetch_and_extract(url, source_id)

    @classmethod
    async def fetch_and_extract(cls, url: str, source_id: str) -> list[RawBlock]:
        video_id = parse_video_url(url)
        if video_id is None:
            raise ValueError(f"Not a recognised YouTube URL: {url}")
        snippets = await asyncio.to_thread(cls._fetch_snippets, video_id)
        return build_transcript_blocks(snippets, source_id)

    @staticmethod
    def _fetch_snippets(video_id: str) -> list[dict]:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )

        api = YouTubeTranscriptApi()
        try:
            transcript = pick_transcript(list(api.list(video_id)))
            if transcript is None:
                raise ValueError(f"Video {video_id} has no transcripts (OQ-59 — ASR is part 2)")
            fetched = transcript.fetch()
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            raise ValueError(f"Video {video_id} has no usable captions: {exc.__class__.__name__}")
        except VideoUnavailable:
            raise ValueError(f"Video {video_id} is unavailable")
        return [{"text": s.text, "start": s.start} for s in fetched.snippets]
