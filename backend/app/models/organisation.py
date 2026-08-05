import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Organisation(Base):
    """Org boundary for `team` visibility (docs/09-organisations.md, supersedes OQ-3).

    Membership lives on users.org_id/org_role — single optional org per user;
    multi-membership is the future *teams* concept, not orgs.
    """

    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Rotatable join secret — sharing it out-of-band is the whole invite flow
    invite_code: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    members: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="organisation",
        foreign_keys="User.org_id",
    )
