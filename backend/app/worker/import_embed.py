"""import.jobs handler — re-embed imported chunks that arrived without usable
vectors (docs/18, OQ-80). One job per import; the namespace is the unit of work.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — full ORM registry before any DB ops
from app.models.chunk import Chunk
from app.models.knowledge_base import KnowledgeBase
from app.models.source import Source
from app.worker.embed import embed_chunks

logger = logging.getLogger(__name__)

_BATCH = 64


async def run_import_embed_job(db: AsyncSession, job: dict) -> None:
    kb_id: str = job["kb_id"]
    vector_namespace: str = job["vector_namespace"]

    while True:
        chunks = list(
            (await db.execute(
                select(Chunk)
                .where(
                    Chunk.vector_namespace == vector_namespace,
                    Chunk.embedding.is_(None),
                )
                .order_by(Chunk.source_id, Chunk.seq)
                .limit(_BATCH)
            )).scalars().all()
        )
        if not chunks:
            break
        embeddings = await embed_chunks([c.text for c in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
            chunk.embedding_model_id = "nomic-embed-text-v1.5"
        await db.commit()
        logger.info("import re-embed: %d chunks for kb %s", len(chunks), kb_id)

    # Everything embedded — flip the imported sources and the KB to ready
    sources = list(
        (await db.execute(select(Source).where(Source.kb_id == kb_id))).scalars().all()
    )
    for s in sources:
        if s.ingestion_status != "embedded":
            s.ingestion_status = "embedded"
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is not None:
        kb.index_status = "ready"
    await db.commit()
