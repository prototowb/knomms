import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Many-to-many: a KnowledgeBase can include multiple Collections
knowledge_base_collection = Table(
    "knowledge_base_collection",
    Base.metadata,
    Column("kb_id", String(36), ForeignKey("knowledge_bases.id"), primary_key=True),
    Column("collection_id", String(36), ForeignKey("collections.id"), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="private"
    )  # private | team | public
    # Namespace used for pgvector RLS isolation — format: kb:{id}
    vector_namespace: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    embedding_model_id: Mapped[str] = mapped_column(String(64), nullable=False, default="nomic-embed-text-v1.5")

    index_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="building"
    )  # building | ready | stale | rebuilding

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

    owner: Mapped["User"] = relationship("User", back_populates="knowledge_bases")  # type: ignore[name-defined]
    collections: Mapped[list["Collection"]] = relationship(  # type: ignore[name-defined]
        "Collection",
        secondary=knowledge_base_collection,
        back_populates="knowledge_bases",
    )
