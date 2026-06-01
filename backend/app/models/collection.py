import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.knowledge_base import knowledge_base_collection

EMBEDDING_DIM = 768  # must match chunks.EMBEDDING_DIM


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="private"
    )  # private | team | public

    forked_from_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id"), nullable=True)
    fork_lineage: Mapped[list[str]] = mapped_column(ARRAY(String(36)), nullable=False, default=list)
    fork_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Board layout: {"mode": "swim-lane"|"canvas", "lanes": [...]}
    layout_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Centroid of all source chunk embeddings — used for semantic recommendation
    board_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="collections")  # type: ignore[name-defined]
    forked_from: Mapped["Collection | None"] = relationship(
        "Collection", remote_side="Collection.id", foreign_keys=[forked_from_id]
    )
    items: Mapped[list["CollectionItem"]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan",
        order_by="CollectionItem.position",
    )
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(  # type: ignore[name-defined]
        "KnowledgeBase",
        secondary=knowledge_base_collection,
        back_populates="collections",
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    added_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lane: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    collection: Mapped["Collection"] = relationship("Collection", back_populates="items")
    source: Mapped["Source"] = relationship("Source")  # type: ignore[name-defined]
