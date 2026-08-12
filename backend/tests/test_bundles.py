"""Unit tests for KB bundle build/validate/plan — pure logic, no DB (KC-103/104)."""

from dataclasses import dataclass, field

from app.domains.knowledge_base.bundles import (
    BUNDLE_FORMAT,
    BUNDLE_VERSION,
    EMBEDDING_DIM,
    MAX_CHUNK_CHARS,
    build_kb_bundle,
    plan_import,
    validate_bundle,
)

MODEL = "nomic-embed-text-v1.5"
VEC = [0.1] * EMBEDDING_DIM


@dataclass
class _Source:
    id: str
    type: str = "web_page"
    title: str = "A page"
    description: str = ""
    raw_url: str | None = "https://example.com/"


@dataclass
class _Chunk:
    source_id: str
    seq: int = 0
    locator: str = "para:1"
    text: str = "some chunk text"
    content_hash: str = "h" * 64
    is_overlap: bool = False
    embedding: list | None = field(default_factory=lambda: list(VEC))
    embedding_model_id: str | None = MODEL


def _bundle(**overrides) -> dict:
    data = build_kb_bundle(
        "My KB",
        [_Source(id="s1"), _Source(id="s2", type="video", raw_url="https://youtu.be/x")],
        [_Chunk("s1"), _Chunk("s2", locator="ts:00:01:33")],
    )
    data.update(overrides)
    return data


# ── build + round-trip ────────────────────────────────────────────────────────


def test_build_maps_ids_to_indexes_and_roundtrips():
    data = _bundle()
    assert data["format"] == BUNDLE_FORMAT and data["version"] == BUNDLE_VERSION
    assert [s["idx"] for s in data["sources"]] == [0, 1]
    assert "s1" not in str(data)  # instance ids never leak
    assert data["chunks"][1]["source_idx"] == 1
    assert validate_bundle(data) is None
    plan = plan_import(data, MODEL)
    assert plan["title"] == "My KB"
    assert plan["needs_embedding"] is False
    assert plan["chunks"][1]["locator"] == "ts:00:01:33"


def test_build_skips_chunks_of_unknown_sources():
    data = build_kb_bundle("t", [_Source(id="s1")], [_Chunk("s1"), _Chunk("ghost")])
    assert len(data["chunks"]) == 1


# ── validate ──────────────────────────────────────────────────────────────────


def test_validate_rejects_wrong_format_and_version():
    assert "format" in validate_bundle(_bundle(format="something-else"))
    assert "version" in validate_bundle(_bundle(version=2))
    assert validate_bundle("not a dict") is not None


def test_validate_rejects_bad_shapes():
    assert "kb.title" in validate_bundle(_bundle(kb={}))
    assert "sources" in validate_bundle(_bundle(sources=[]))
    data = _bundle()
    data["sources"][1]["idx"] = 5
    assert "contiguous" in validate_bundle(data)
    data = _bundle()
    data["chunks"][0]["source_idx"] = 99
    assert "out of range" in validate_bundle(data)
    data = _bundle()
    data["chunks"][0]["text"] = "x" * (MAX_CHUNK_CHARS + 1)
    assert "text" in validate_bundle(data)


def test_validate_rejects_bad_embedding_dims():
    data = _bundle()
    data["chunks"][0]["embedding"] = [0.1, 0.2]
    assert str(EMBEDDING_DIM) in validate_bundle(data)
    data["chunks"][0]["embedding"] = None
    assert validate_bundle(data) is None


# ── plan ──────────────────────────────────────────────────────────────────────


def test_plan_drops_vectors_on_model_mismatch():
    data = _bundle()
    data["chunks"][0]["embedding_model_id"] = "some-other-model"
    plan = plan_import(data, MODEL)
    assert plan["needs_embedding"] is True
    assert plan["chunks"][0]["embedding"] is None
    assert plan["chunks"][1]["embedding"] is not None  # matching chunk kept


def test_plan_degrades_unknown_source_types():
    data = _bundle()
    data["sources"][0]["type"] = "hologram"
    plan = plan_import(data, MODEL)
    assert plan["sources"][0]["type"] == "plain_text"
    assert plan["sources"][1]["type"] == "video"


def test_plan_computes_missing_content_hash():
    data = _bundle()
    data["chunks"][0]["content_hash"] = ""
    plan = plan_import(data, MODEL)
    assert len(plan["chunks"][0]["content_hash"]) == 64
