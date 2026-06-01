"""Ingestion pipeline — orchestrates fetch → extract → chunk → dedup → embed → persist.

Called by the worker consumer for each Redis Streams job message.
"""

import json
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.domains.ingestion.blocks import RawBlock
from app.domains.ingestion.chunker import chunk_blocks
from app.domains.ingestion.extractors.pdf import PDFExtractor
from app.domains.ingestion.extractors.web import WebExtractor
from app.models.chunk import Chunk
from app.models.source import Source
from app.worker.embed import embed_chunks

logger = logging.getLogger(__name__)

_pdf_extractor = PDFExtractor()
_web_extractor = WebExtractor()


async def run_ingestion_pipeline(db: AsyncSession, job: dict) -> None:
    source_id: str = job["source_id"]
    vector_namespace: str = job["vector_namespace"]
    is_upload: bool = job.get("upload", "0") == "1"

    source = await db.get(Source, source_id)
    if source is None:
        logger.error("Source %s not found — skipping job", source_id)
        return

    try:
        await _set_status(db, source, "processing", vector_namespace)
        await _publish_progress(source_id, "processing", 10)

        # Stage 1: fetch raw content
        raw_content = await _fetch_content(source, is_upload)
        await _publish_progress(source_id, "processing", 25)

        # Stage 2: extract → RawBlock[]
        raw_blocks = await _extract(source, raw_content)
        await _publish_progress(source_id, "processing", 40)

        # Stage 3: chunk
        chunk_dicts = chunk_blocks(raw_blocks, source_id, vector_namespace)
        await _set_status(db, source, "chunked", vector_namespace)
        await _publish_progress(source_id, "chunked", 55)

        # Stage 4: dedup — skip chunks whose hash already exists for this source
        new_chunks = await _dedup(db, source_id, chunk_dicts)
        await _publish_progress(source_id, "processing", 65)

        # Stage 5: embed new chunks
        if new_chunks:
            texts = [c["text"] for c in new_chunks]
            embeddings = await embed_chunks(texts)
            for chunk_dict, embedding in zip(new_chunks, embeddings):
                chunk_dict["embedding"] = embedding
                chunk_dict["embedding_model_id"] = "nomic-embed-text-v1.5"

        await _publish_progress(source_id, "processing", 85)

        # Stage 6: persist chunks + vectors
        for chunk_dict in new_chunks:
            db.add(Chunk(**chunk_dict))
        await db.commit()

        await _set_status(db, source, "embedded", vector_namespace)
        await _publish_progress(source_id, "embedded", 100)

        # Stage 7: publish source.embedded event for downstream consumers
        redis = await get_redis()
        await redis.publish(
            "source.embedded",
            json.dumps({"source_id": source_id, "kb_ids": [job["kb_id"]]}),
        )

    except Exception as exc:
        logger.exception("Ingestion failed for source %s", source_id)
        await _set_status(db, source, "failed", vector_namespace)
        await _publish_progress(source_id, "failed", 0)
        raise


async def _fetch_content(source: Source, is_upload: bool) -> bytes:
    if is_upload:
        redis = await get_redis()
        data = await redis.getdel(f"upload:{source.id}")
        if data is None:
            raise ValueError(f"Upload data expired or missing for source {source.id}")
        return data if isinstance(data, bytes) else data.encode()

    if source.raw_url:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0),
        ) as client:
            resp = await client.get(source.raw_url)
            resp.raise_for_status()
            return resp.content

    raise ValueError(f"Source {source.id} has neither raw_url nor upload data")


async def _extract(source: Source, content: bytes) -> list[RawBlock]:
    if source.type == "pdf":
        return await _pdf_extractor.extract(content, source.id)
    if source.type == "web_page":
        return await _web_extractor.extract(content, source.id, url=source.raw_url)
    # Fallback: treat as plain text
    text = content.decode("utf-8", errors="replace")
    return [
        RawBlock(
            text=para.strip(),
            source_id=source.id,
            block_index=i,
            page_or_position=f"para:{i + 1}",
        )
        for i, para in enumerate(text.split("\n\n"))
        if para.strip()
    ]


async def _dedup(db: AsyncSession, source_id: str, chunk_dicts: list[dict]) -> list[dict]:
    """Return only chunks whose content_hash is not already in DB for this source."""
    if not chunk_dicts:
        return []

    hashes = [c["content_hash"] for c in chunk_dicts]
    existing = await db.execute(
        select(Chunk.content_hash).where(
            Chunk.source_id == source_id,
            Chunk.content_hash.in_(hashes),
        )
    )
    existing_hashes = {row[0] for row in existing.all()}
    return [c for c in chunk_dicts if c["content_hash"] not in existing_hashes]


async def _set_status(db: AsyncSession, source: Source, status: str, vector_namespace: str) -> None:
    source.ingestion_status = status
    await db.commit()


async def _publish_progress(source_id: str, status: str, progress_pct: int) -> None:
    redis = await get_redis()
    await redis.publish(
        f"source:{source_id}:progress",
        json.dumps({"status": status, "progress_pct": progress_pct}),
    )
