import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FederationFeed(Base):
    """Capability-URL feed for a KB (docs/23, OQ-95) — possession of the
    slug grants read; revoke by deleting the row (re-mint = rotation)."""

    __tablename__ = "federation_feeds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class FederationSubscription(Base):
    """A local mirror KB tracking a remote bundle feed (docs/23, OQ-96/97).

    The kb_id's existence here makes that KB a read-only mirror (OQ-98);
    deleting the row frees it back into an ordinary local KB.
    """

    __tablename__ = "federation_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    feed_url: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
