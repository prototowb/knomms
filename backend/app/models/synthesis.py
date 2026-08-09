import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Synthesis(Base):
    """A saved multi-source synthesis (docs/17, OQ-69) — the author's record.

    citations is a snapshot of the SSE citations dict (chunks are re-indexed;
    the passage-excerpt precedent). Author-owned: reads/deletes are scoped to
    user_id; sharing goes through board projection.
    """

    __tablename__ = "syntheses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class SynthesisSourceProjection(Base):
    """Dedup row for synthesis → board-KB projection (docs/17, OQ-71) — the
    asset_source_projections twin: re-adding into the same KB reuses the Source."""

    __tablename__ = "synthesis_source_projections"
    __table_args__ = (
        UniqueConstraint("synthesis_id", "kb_id", name="uq_synthesis_projection_kb"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    synthesis_id: Mapped[str] = mapped_column(
        ForeignKey("syntheses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
