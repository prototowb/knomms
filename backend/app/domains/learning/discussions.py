"""Passage-anchored discussion threads on path concepts (docs/13, OQ-40–42).

The cohort is whoever can read the path — every guard here delegates to
LearningService's readable-path helpers, exactly as notes/progress do. Threads
list newest-first; posts within a thread oldest-first (OQ-42).
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.learning.service import LearningService
from app.models.learning import DiscussionPost, DiscussionThread
from app.models.user import User


def resolve_passage_anchor(passage_chunk_id: str | None, source_passages: list) -> str:
    """Validate an optional passage anchor against a concept's source_passages
    and return the excerpt to snapshot ('' for unanchored threads).

    Pure — raises ValueError when the anchor isn't one of the concept's
    passages (chunk ids are soft references; anchoring to arbitrary chunks
    would leak content from other KBs into the thread header).
    """
    if passage_chunk_id is None:
        return ""
    for p in source_passages or []:
        if p.get("chunk_id") == passage_chunk_id:
            return p.get("excerpt") or ""
    raise ValueError("passage_chunk_id is not one of this concept's source passages")


def can_delete_post(post_author_id: str, requester_id: str, path_owner_id: str) -> bool:
    """Post author may delete their own post; the path owner moderates (OQ-41)."""
    return requester_id == post_author_id or requester_id == path_owner_id


class DiscussionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._learning = LearningService(db)

    async def list_threads(
        self, path_id: str, concept_id: str, user: User, limit: int = 50, offset: int = 0
    ) -> list[tuple[DiscussionThread, int]]:
        """Threads on a concept, newest first, each with its post count."""
        path = await self._learning._get_readable_concept(path_id, concept_id, user)
        # Hard-mode gate (docs/14, OQ-48): thread bodies quote locked passages
        await self._learning.ensure_not_locked(path, concept_id, user)
        post_count = (
            select(func.count(DiscussionPost.id))
            .where(DiscussionPost.thread_id == DiscussionThread.id)
            .correlate(DiscussionThread)
            .scalar_subquery()
        )
        stmt = (
            select(DiscussionThread, post_count)
            .where(DiscussionThread.concept_id == concept_id)
            .options(selectinload(DiscussionThread.author))
            .order_by(DiscussionThread.created_at.desc(), DiscussionThread.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def create_thread(
        self,
        path_id: str,
        concept_id: str,
        user: User,
        title: str,
        body: str,
        passage_chunk_id: str | None,
    ) -> DiscussionThread:
        path = await self._learning.get_readable_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        concept = next((c for c in path.concepts if c.id == concept_id), None)
        if concept is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Concept not found")
        await self._learning.ensure_not_locked(path, concept_id, user)

        if not title.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="title must not be empty")
        try:
            excerpt = resolve_passage_anchor(passage_chunk_id, concept.source_passages)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

        thread = DiscussionThread(
            concept_id=concept_id,
            created_by=user.id,
            passage_chunk_id=passage_chunk_id,
            passage_excerpt=excerpt,
            title=title.strip(),
            body=body,
        )
        self.db.add(thread)
        await self.db.commit()
        return await self._reload_thread(thread.id)

    async def get_thread(self, path_id: str, thread_id: str, user: User) -> DiscussionThread:
        """Thread with posts (ASC) — 404 unless its concept belongs to a path
        the user can read."""
        path = await self._learning.get_readable_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        thread = await self._reload_thread(thread_id)
        if thread is None or not any(c.id == thread.concept_id for c in path.concepts):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Thread not found")
        # Gates thread reads and (via create_post's call here) replies; post
        # deletion stays ungated (docs/14, OQ-50)
        await self._learning.ensure_not_locked(path, thread.concept_id, user)
        return thread

    async def create_post(self, path_id: str, thread_id: str, user: User, body: str) -> DiscussionPost:
        if not body.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="body must not be empty")
        await self.get_thread(path_id, thread_id, user)

        post = DiscussionPost(thread_id=thread_id, user_id=user.id, body=body)
        self.db.add(post)
        await self.db.commit()
        stmt = (
            select(DiscussionPost)
            .where(DiscussionPost.id == post.id)
            .options(selectinload(DiscussionPost.author))
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def delete_post(self, path_id: str, thread_id: str, post_id: str, user: User) -> None:
        path = await self._learning.get_readable_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        thread = await self.db.get(DiscussionThread, thread_id)
        if thread is None or not any(c.id == thread.concept_id for c in path.concepts):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Thread not found")

        post = await self.db.get(DiscussionPost, post_id)
        if post is None or post.thread_id != thread_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
        if not can_delete_post(post.user_id, user.id, path.user_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the author or the path owner can delete a post")

        await self.db.delete(post)
        await self.db.commit()

    async def _reload_thread(self, thread_id: str) -> DiscussionThread | None:
        stmt = (
            select(DiscussionThread)
            .where(DiscussionThread.id == thread_id)
            .options(
                selectinload(DiscussionThread.author),
                selectinload(DiscussionThread.posts).selectinload(DiscussionPost.author),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
