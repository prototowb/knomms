"""Retrieval service — M1: dense-only pgvector cosine search, namespace-scoped."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.retrieval.types import RetrievedChunk
from app.models.chunk import Chunk

HNSW_EF_SEARCH = 40  # recall/latency trade-off for HNSW; increase for higher recall


class RetrievalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def retrieve(
        self,
        query_embedding: list[float],
        vector_namespace: str,
        top_k: int = 10,
        source_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Return top_k chunks from the given namespace, ordered by cosine
        similarity — optionally scoped to one source (balanced multi-source
        retrieval, docs/16 OQ-64)."""
        # Set ef_search for this transaction — controls HNSW recall
        await self.db.execute(text(f"SET LOCAL hnsw.ef_search = {HNSW_EF_SEARCH}"))

        conditions = [
            Chunk.vector_namespace == vector_namespace,
            Chunk.embedding.is_not(None),
        ]
        if source_id is not None:
            conditions.append(Chunk.source_id == source_id)

        # pgvector cosine distance operator: <=>
        # Hits the ix_chunks_embedding_hnsw HNSW index (vector_cosine_ops)
        stmt = (
            select(
                Chunk.id,
                Chunk.source_id,
                Chunk.locator,
                Chunk.text,
                Chunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(*conditions)
            .order_by("distance")
            .limit(top_k)
        )

        rows = (await self.db.execute(stmt)).all()
        return [
            RetrievedChunk(
                chunk_id=row.id,
                source_id=row.source_id,
                locator=row.locator,
                text=row.text,
                score=float(row.distance),
            )
            for row in rows
        ]
