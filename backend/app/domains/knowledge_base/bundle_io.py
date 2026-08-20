"""Bundle materialization — the DB half shared by part-1 import and part-2
federation subscribe/sync (docs/23 §4). The pure half lives in bundles.py.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.knowledge_base import KnowledgeBase
from app.models.source import Source


async def wipe_kb_sources(db: AsyncSession, kb: KnowledgeBase) -> None:
    """Delete every Source in the KB (chunks + projection rows cascade).

    Used by sync's full-replace (OQ-97). Callers must guarantee no
    HarnessStudyDoc references these sources (its source_id FK has no
    ON DELETE) — mirror KBs are created by subscribe and can never be
    study KBs, so the guarantee holds by construction.
    """
    source_ids = (
        (await db.execute(select(Source.id).where(Source.kb_id == kb.id))).scalars().all()
    )
    if source_ids:
        await db.execute(delete(Source).where(Source.id.in_(source_ids)))
        await db.flush()


def materialize_plan(db: AsyncSession, user_id: str, kb: KnowledgeBase, plan: dict) -> bool:
    """Create Source + Chunk rows from a plan_import result — fresh ids,
    namespace-stamped (docs/18 OQ-78). Sets kb.index_status. Returns
    needs_embedding; the CALLER commits (before any enqueue, OQ-73) and
    enqueues import.jobs when True. Synchronous: only stages ORM objects.
    """
    needs_embedding: bool = plan["needs_embedding"]
    source_ids: list[str] = []
    for s in plan["sources"]:
        sid = str(uuid.uuid4())
        source_ids.append(sid)
        db.add(Source(
            id=sid,
            owner_user_id=user_id,
            type=s["type"],
            title=s["title"],
            description=s["description"] or None,
            raw_url=s["raw_url"],
            kb_id=kb.id,
            ingestion_status="pending" if needs_embedding else "embedded",
        ))
    for c in plan["chunks"]:
        db.add(Chunk(
            source_id=source_ids[c["source_idx"]],
            seq=c["seq"],
            locator=c["locator"],
            text=c["text"],
            content_hash=c["content_hash"],
            is_overlap=c["is_overlap"],
            embedding=c["embedding"],
            embedding_model_id=c["embedding_model_id"],
            vector_namespace=kb.vector_namespace,
        ))
    kb.index_status = "building" if needs_embedding else "ready"
    return needs_embedding
