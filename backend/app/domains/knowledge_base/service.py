"""KnowledgeBase service — M1 scope: get-or-create the default KB for a user."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.models.user import User


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

    async def get_by_id(self, kb_id: str, user: User) -> KnowledgeBase | None:
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.owner_user_id == user.id,  # ownership check
            )
        )
        return result.scalar_one_or_none()
