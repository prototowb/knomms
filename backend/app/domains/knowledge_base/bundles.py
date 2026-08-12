"""Portable KB bundles (docs/18, OQ-75–80) — export, validation, import planning.

Everything here is pure: DB rows in, dicts out. Instance ids never enter a
bundle (sources are referenced by index); bundles are untrusted input on the
way back in, so validation bounds every axis before anything touches the DB.
"""

BUNDLE_FORMAT = "knomms-kb-bundle"
BUNDLE_VERSION = 1

MAX_SOURCES = 500
MAX_CHUNKS = 50_000
MAX_CHUNK_CHARS = 20_000
MAX_TITLE_CHARS = 200
EMBEDDING_DIM = 768

KNOWN_SOURCE_TYPES = frozenset(
    {"web_page", "pdf", "video", "audio", "image", "plain_text", "code_file", "epub",
     "prompt_asset", "synthesis"}
)


def build_kb_bundle(kb_title: str, sources: list, chunks: list) -> dict:
    """Assemble the export document (OQ-75).

    `sources`/`chunks` are ORM rows or anything with the same attributes.
    Instance ids are mapped to bundle-local indexes.
    """
    index_of = {s.id: i for i, s in enumerate(sources)}
    return {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "kb": {"title": kb_title},
        "sources": [
            {
                "idx": i,
                "type": s.type,
                "title": s.title,
                "description": s.description or "",
                "raw_url": s.raw_url,
            }
            for i, s in enumerate(sources)
        ],
        "chunks": [
            {
                "source_idx": index_of[c.source_id],
                "seq": c.seq,
                "locator": c.locator,
                "text": c.text,
                "content_hash": c.content_hash,
                "is_overlap": bool(c.is_overlap),
                "embedding": list(c.embedding) if c.embedding is not None else None,
                "embedding_model_id": c.embedding_model_id,
            }
            for c in chunks
            if c.source_id in index_of
        ],
    }


def validate_bundle(data) -> str | None:
    """Bound every axis of an untrusted bundle (OQ-79).

    Returns a precise error string, or None when the bundle is importable.
    """
    if not isinstance(data, dict):
        return "bundle must be a JSON object"
    if data.get("format") != BUNDLE_FORMAT:
        return f"format must be '{BUNDLE_FORMAT}'"
    if data.get("version") != BUNDLE_VERSION:
        return f"unsupported bundle version {data.get('version')!r} (this instance reads version {BUNDLE_VERSION})"

    kb = data.get("kb")
    if not isinstance(kb, dict) or not isinstance(kb.get("title"), str) or not kb["title"].strip():
        return "kb.title is required"

    sources = data.get("sources")
    if not isinstance(sources, list) or not (1 <= len(sources) <= MAX_SOURCES):
        return f"sources must be a list of 1–{MAX_SOURCES}"
    for i, s in enumerate(sources):
        if not isinstance(s, dict) or s.get("idx") != i:
            return f"sources[{i}] must be an object with idx={i} (contiguous indexes)"
        if not isinstance(s.get("title"), str) or not s["title"].strip():
            return f"sources[{i}].title is required"

    chunks = data.get("chunks")
    if not isinstance(chunks, list) or not (1 <= len(chunks) <= MAX_CHUNKS):
        return f"chunks must be a list of 1–{MAX_CHUNKS}"
    for i, c in enumerate(chunks):
        if not isinstance(c, dict):
            return f"chunks[{i}] must be an object"
        if not isinstance(c.get("source_idx"), int) or not (0 <= c["source_idx"] < len(sources)):
            return f"chunks[{i}].source_idx out of range"
        text = c.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHUNK_CHARS:
            return f"chunks[{i}].text must be a non-empty string ≤ {MAX_CHUNK_CHARS} chars"
        emb = c.get("embedding")
        if emb is not None:
            if not isinstance(emb, list) or len(emb) != EMBEDDING_DIM or not all(
                isinstance(v, (int, float)) for v in emb
            ):
                return f"chunks[{i}].embedding must be null or a list of {EMBEDDING_DIM} numbers"
    return None


def plan_import(data: dict, target_embedding_model_id: str) -> dict:
    """Normalize a validated bundle into insertable rows (OQ-76/78).

    Fresh ids are the caller's job (they need uuid); this returns clean field
    dicts plus `needs_embedding`: chunks keep their vectors only when their
    model matches the target KB's, otherwise vectors are dropped for the
    import.jobs re-embed pass. Unknown source types degrade to plain_text.
    """
    sources = [
        {
            "type": s.get("type") if s.get("type") in KNOWN_SOURCE_TYPES else "plain_text",
            "title": str(s["title"])[:MAX_TITLE_CHARS],
            "description": str(s.get("description") or ""),
            "raw_url": s.get("raw_url") if isinstance(s.get("raw_url"), str) else None,
        }
        for s in data["sources"]
    ]

    import hashlib

    chunks = []
    needs_embedding = False
    for c in data["chunks"]:
        keep = (
            c.get("embedding") is not None
            and c.get("embedding_model_id") == target_embedding_model_id
        )
        if not keep:
            needs_embedding = True
        chunks.append(
            {
                "source_idx": c["source_idx"],
                "seq": int(c.get("seq") or 0),
                "locator": str(c.get("locator") or "para:1")[:128],
                "text": c["text"],
                "content_hash": (
                    str(c["content_hash"])[:64]
                    if c.get("content_hash")
                    else hashlib.sha256(c["text"].encode()).hexdigest()
                ),
                "is_overlap": bool(c.get("is_overlap")),
                "embedding": c["embedding"] if keep else None,
                "embedding_model_id": target_embedding_model_id if keep else None,
            }
        )

    return {
        "title": str(data["kb"]["title"]).strip()[:MAX_TITLE_CHARS],
        "sources": sources,
        "chunks": chunks,
        "needs_embedding": needs_embedding,
    }
