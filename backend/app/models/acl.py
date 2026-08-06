import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AclGrant(Base):
    """Per-resource share (docs/10-teams-and-acls.md OQ-16/17/18).

    resource_id is polymorphic — no FK. None of the grantable resource types
    (kb/asset/harness) has a delete endpoint today; any domain that grows one
    must delete its grants in the same service call.
    """

    __tablename__ = "acl_grants"
    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "principal_type",
            "principal_id",
            name="uq_acl_grants_resource_principal",
        ),
        Index("ix_acl_grants_principal", "principal_type", "principal_id"),
        Index("ix_acl_grants_resource", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type: Mapped[str] = mapped_column(String(10), nullable=False)  # kb | asset | harness
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # user | team
    principal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    permission: Mapped[str] = mapped_column(String(10), nullable=False)  # viewer | editor
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
