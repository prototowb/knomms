import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # web_page | pdf | video | audio | image | plain_text | code_file | epub
    raw_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    visibility: Mapped[str] = mapped_column(
        String(10), nullable=False, default="private"
    )  # private | team | public
    ingestion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | chunked | embedded | failed | stale
    ingestion_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

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

    owner: Mapped["User"] = relationship("User", back_populates="sources")  # type: ignore[name-defined]
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="source", cascade="all, delete-orphan")  # type: ignore[name-defined]
