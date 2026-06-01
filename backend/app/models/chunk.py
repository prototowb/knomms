import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

EMBEDDING_DIM = 768  # nomic-embed-text-v1.5 default (MRL-compressible to 256)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    locator: Mapped[str] = mapped_column(String(128), nullable=False)  # "page:3", "ts:01:23:45"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_overlap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    source: Mapped["Source"] = relationship("Source", back_populates="chunks")  # type: ignore[name-defined]

    __table_args__ = (
        # HNSW index — created CONCURRENTLY in the migration after initial data load.
        # Defined here so Alembic can manage it; the migration uses CREATE INDEX CONCURRENTLY.
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_source_seq", "source_id", "seq"),
        Index("ix_chunks_hash_source", "content_hash", "source_id"),
    )
