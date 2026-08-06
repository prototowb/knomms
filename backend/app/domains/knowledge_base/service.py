"""KnowledgeBase service — CRUD, ownership, and readable-access lookups."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

VISIBILITIES = frozenset({"private", "team", "public"})


class KnowledgeBaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_default(self, user: User) -> KnowledgeBase:
        """Return the user's default KB, creating one if it doesn't exist yet."""
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.owner_user_id == user.id)
            .order_by(KnowledgeBase.created_at)
            .limit(1)
        )
        kb = result.scalar_one_or_none()
        if kb is not None:
            return kb

        kb_id = str(uuid.uuid4())
        kb = KnowledgeBase(
            id=kb_id,
            owner_user_id=user.id,
            title=f"{user.display_name}'s Knowledge Base",
            vector_namespace=f"kb:{kb_id}",
            index_status="building",
        )
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def create(self, user: User, title: str, visibility: str = "private") -> KnowledgeBase:
        """Always create a new KB with a fresh, isolated vector_namespace."""
        if visibility not in VISIBILITIES:
            visibility = "private"
        kb_id = str(uuid.uuid4())
        kb = KnowledgeBase(
            id=kb_id,
            owner_user_id=user.id,
            title=title,
            visibility=visibility,
            vector_namespace=f"kb:{kb_id}",
            index_status="building",
        )
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def list_for_user(self, user: User) -> list[KnowledgeBase]:
        """Own KBs plus KBs shared with the user via an ACL grant — the
        grantee's way of finding what was shared (docs/10 §5)."""
        from app.domains.organisations.predicates import grant_subquery

        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                or_(
                    KnowledgeBase.owner_user_id == user.id,
                    KnowledgeBase.id.in_(grant_subquery("kb", user)),
                )
            )
            .options(selectinload(KnowledgeBase.owner))
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, kb_id: str, user: User) -> KnowledgeBase | None:
        """Owner-only lookup — the guard for every WRITE path (ingest, project,
        create learning path). Do not relax; reads go through get_readable_by_id."""
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.owner_user_id == user.id,  # ownership check
            )
            .options(selectinload(KnowledgeBase.owner))
        )
        return result.scalar_one_or_none()

    async def get_readable_by_id(self, kb_id: str, user: User) -> KnowledgeBase | None:
        """Read lookup: the owner, anyone for public, same-org users for team
        (docs/09 OQ-7), or any ACL grantee (docs/10 OQ-16)."""
        from app.domains.organisations.predicates import readable_clause

        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                KnowledgeBase.id == kb_id,
                or_(
                    KnowledgeBase.owner_user_id == user.id,
                    readable_clause(KnowledgeBase, "kb", user),
                ),
            )
            .options(selectinload(KnowledgeBase.owner))
        )
        return result.scalar_one_or_none()

    async def get_editable_by_id(self, kb_id: str, user: User) -> KnowledgeBase | None:
        """Write guard for the OQ-18 surface only (add sources). Metadata,
        visibility, and grant management stay on get_by_id (owner)."""
        from app.domains.organisations.predicates import editable_clause

        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                KnowledgeBase.id == kb_id,
                editable_clause(KnowledgeBase, "kb", user),
            )
            .options(selectinload(KnowledgeBase.owner))
        )
        return result.scalar_one_or_none()

    async def list_public(self, limit: int = 50, offset: int = 0) -> list[KnowledgeBase]:
        """Public KBs for explore — no auth required."""
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.visibility == "public")
            .options(selectinload(KnowledgeBase.owner))
            .order_by(KnowledgeBase.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
