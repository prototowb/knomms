# Video Transcript Ingestion, Part 1 — Design (V2 roadmap #2)

> Status: **proposed** (2026-08-06). First slice of the roadmap's #2 V2
> priority ("Video/audio ingestion — transcript extraction with timestamp
> locators; dramatically expands addressable source types",
> `docs/06-roadmap.md` §V2). This part ships **YouTube caption/transcript
> ingestion with timestamp locators**; local ASR (Whisper) for arbitrary
> video/audio stays in part 2. Proposed sprint: **v0.12.0 = KC-092–095**.

## 1. Problem

Every knowledge worker's corpus includes talks, lectures, and tutorials —
and the platform can't touch any of it. The MVP deferred video wholesale,
but the architecture already reserved the seams: `Source.type` includes
`video`, and the `RawBlock` contract documents `ts:HH:MM:SS` locators
(`blocks.py`). Nothing downstream needs to change — chunker, embedding,
retrieval, Q&A citations, curriculum grounding, and passage-anchored
discussion all operate on blocks and locators.

## 2. Why captions first (not ASR)

Most lecture/talk content on YouTube already has captions (manual or auto).
Fetching them is a metadata request — no model, no GPU, no long-running job,
no new heavyweight dependency — while local Whisper on the reference
hardware (4 CPU cores) would make a 30-minute video a ~30-minute ingestion
job and bloat the image by gigabytes. Part 1 therefore ingests the
transcript that already exists; part 2 can add local ASR behind the same
`video` source type for self-hosted media files.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-53 | Scope | YouTube URLs only (`youtube.com/watch`, `youtu.be/…`, `youtube.com/shorts/…`, `/live/…`, `/embed/…`); other video platforms and uploaded media files deferred | One well-known transcript surface; the URL-detection helper is pure and extensible |
| OQ-54 | Transcript dependency | `youtube-transcript-api` (pure-Python, no API key), called via `asyncio.to_thread` in the async worker | Battle-tested against InnerTube; hand-rolling the caption-track scrape via httpx is the brittle part of the problem, not the interesting part. Sync client is fine off the event loop |
| OQ-55 | Type detection | `submit_url` runs pure `parse_video_url(url) → video_id \| None`; a match stamps `type="video"` (existing enum value), else `web_page` as today | The Source row must carry the right type *before* the worker runs — the pipeline dispatches extractors on it |
| OQ-56 | Block shape | Pure `build_transcript_blocks(snippets, source_id)`: consecutive caption snippets accumulate into one block until ~400 chars, closing on sentence end where possible; locator = `ts:HH:MM:SS` of the block's first snippet (the documented RawBlock convention) | Raw snippets are 2–8 words — far too small to embed or cite. ~400-char windows match the prose paragraph granularity the chunker was tuned for; the locator stays honest (start of what you'll hear) |
| OQ-57 | Language choice | Prefer manually-created transcripts over auto-generated, English variants first, else the first available | `youtube-transcript-api` exposes the distinction; manual captions are markedly cleaner. No translation — corpus fidelity over convenience |
| OQ-58 | Worker fetch path | `video` sources skip `_fetch_content` entirely — the extractor owns its own fetch (`fetch_and_extract(raw_url, source_id)`), mirroring `WebExtractor`'s shape | Fetching the watch page HTML would be wasted bytes; the transcript API needs the video id, not the page |
| OQ-59 | Missing captions | Ingestion fails with status `failed` (existing pipeline path); the specific reason is logged | Part 1 has no fallback (ASR is part 2). A failed source with a clear log beats a silent empty KB |
| OQ-60 | Title | Best-effort oEmbed lookup (`youtube.com/oembed`) at submit time, falling back to `youtube:{video_id}` | oEmbed needs no key and one GET; a human title on the source card matters for boards/search attribution. Failure must never block submission |
| OQ-61 | Timestamp deep links | Frontends render a `ts:HH:MM:SS` locator on a video source as a link to `watch?v={id}&t={seconds}s` — in KB search results and learn-page source passages | This is the payoff of timestamp locators: citation → the exact moment in the talk. Needs the source's `raw_url`/type alongside the locator (search results already carry source attribution; learn passages carry `source_id`) |
| OQ-62 | Storage | Nothing new is persisted beyond chunks — no MinIO write, re-ingest (e.g. board fork) re-fetches like `web_page` does | Transcripts are small and re-fetchable; matches the existing URL-source contract |

## 4. Backend changes

- **New** `ingestion/extractors/video.py`:
  - `parse_video_url(url) → str | None` — pure, handles the OQ-53 URL forms
    (query param `v=`, short/embed/shorts/live path forms, ignores playlists).
  - `build_transcript_blocks(snippets, source_id) → list[RawBlock]` — pure;
    snippets are `{text, start}` dicts; blocks per OQ-56 with `ts:` locators.
  - `VideoExtractor.fetch_and_extract(url, source_id)` — resolves the video
    id, lists transcripts (manual > auto, English first, per OQ-57), fetches
    via `asyncio.to_thread`, returns blocks. Raises `ValueError` with a
    precise message when no transcript exists (OQ-59).
- `ingestion/service.py`: `submit_url` calls `parse_video_url`; on a match
  stamps `type="video"` and resolves the title via oEmbed (best-effort,
  `httpx`, 5s timeout, OQ-60).
- `worker/pipeline.py`: `video` branch dispatches to
  `VideoExtractor.fetch_and_extract` before the generic content fetch
  (OQ-58).
- `pyproject.toml`: `youtube-transcript-api` under the ingestion extra.
- Tests (pure-logic suite constraint): URL-parsing matrix, block
  accumulation/locator formatting, transcript-selection preference order.

## 5. Frontend changes

- Source cards (KB workspace sources tab, board cards): `video` type badge,
  same pattern as the existing `prompt_asset` handling.
- KB search results: when the hit's source is a video, render the chunk
  locator as a clickable timestamp deep link (OQ-61).
- Learn page source passages: same deep link on `ts:` locators when the
  passage's source is a video (passage dicts carry `source_id`; the page
  already fetches nothing extra — resolve via the KB sources list only where
  it is already loaded, otherwise render the plain locator).

## 6. Non-goals (part 2 candidates)

- Local ASR (Whisper) for uploaded media files and caption-less videos
- Non-YouTube platforms (Vimeo, PeerTube) — `parse_video_url` is the seam
- Translated transcripts (OQ-57)
- Embedded video player / in-app seeking — deep links to YouTube suffice
- Image OCR (the roadmap's other deferred ingestion type)

## 7. Verification plan (KC-095)

1. Unit: URL matrix (watch/short/shorts/embed/live/playlist-noise/non-video),
   block grouping (char cap, sentence closing, locator format, empty input),
   transcript preference order.
2. Live (Colima): submit a captioned YouTube URL → source type `video`,
   human title, ingestion completes; chunks carry `ts:` locators; KB
   semantic search returns the video chunk with a working deep link;
   Q&A citation resolves; curriculum generation over the video KB produces
   concepts whose source passages carry timestamp locators; caption-less
   video fails cleanly with `failed` status; web-page regression (unchanged
   type detection for ordinary URLs).
3. Regression: full pytest; vue-tsc clean.
