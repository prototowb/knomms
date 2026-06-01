"""Curation service — boards (collections), fork, semantic search, curator profiles."""

import uuid
from statistics import mean

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import get_redis
from app.domains.curation.types import build_fork_lineage
from app.domains.ingestion.service import STREAM_KEY
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.chunk import Chunk
from app.models.collection import Collection, CollectionItem
from app.models.source import Source
from app.models.user import User

_QUALITY_FLOOR_ITEMS = 3   # min sources to appear in trending / recommendations
_SUMMARY_PROMPT = """\
You are summarizing a curated knowledge board for a discovery platform.

Board title: {title}
Board description: {description}
Sources in this board ({count} total):
{source_list}

Write a 2-3 sentence summary of what this board covers and what a learner will gain from it.
End your summary with one sentence identifying a notable gap or limitation in the current coverage.
Respond with plain prose only — no headers, no bullet points, no markdown."""


class BoardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── read operations ───────────────────────────────────────────────────────

    async def get_public_board(self, board_id: str) -> Collection | None:
        stmt = (
            select(Collection)
            .where(Collection.id == board_id, Collection.visibility == "public")
            .options(
                selectinload(Collection.items).selectinload(CollectionItem.source),
                selectinload(Collection.owner),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_board_for_owner(self, board_id: str, user: User) -> Collection | None:
        stmt = (
            select(Collection)
            .where(Collection.id == board_id, Collection.owner_user_id == user.id)
            .options(
                selectinload(Collection.items).selectinload(CollectionItem.source),
                selectinload(Collection.owner),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_public_boards(
        self,
        sort: str = "trending",
        limit: int = 20,
        offset: int = 0,
    ) -> list[Collection]:
        stmt = (
            select(Collection)
            .where(
                Collection.visibility == "public",
                # Quality floor: only surface boards with enough sources
                select(func.count(CollectionItem.id))
                .where(CollectionItem.collection_id == Collection.id)
                .scalar_subquery() >= _QUALITY_FLOOR_ITEMS,
            )
            .options(selectinload(Collection.owner))
        )
        if sort == "trending":
            stmt = stmt.order_by(Collection.fork_count.desc(), Collection.created_at.desc())
        else:
            stmt = stmt.order_by(Collection.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_boards_semantic(self, query_text: str, limit: int = 10) -> list[Collection]:
        """Find public boards semantically close to query_text.

        Embeds the query, then ranks boards by cosine distance to board_embedding.
        Boards without a board_embedding (not yet indexed) are excluded.
        """
        from app.domains.generation.ollama import embed

        embeddings = await embed([query_text])
        query_vec = embeddings[0]

        stmt = (
            select(
                Collection,
                Collection.board_embedding.cosine_distance(query_vec).label("distance"),
            )
            .where(
                Collection.visibility == "public",
                Collection.board_embedding.is_not(None),
            )
            .options(selectinload(Collection.owner))
            .order_by("distance")
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [row.Collection for row in result.all()]

    async def get_curator_profile(self, handle: str) -> tuple[User, list[Collection]] | None:
        user = (
            await self.db.execute(select(User).where(User.handle == handle))
        ).scalar_one_or_none()
        if user is None:
            return None

        boards = list(
            (
                await self.db.execute(
                    select(Collection)
                    .where(
                        Collection.owner_user_id == user.id,
                        Collection.visibility == "public",
                    )
                    .options(selectinload(Collection.items))
                    .order_by(Collection.fork_count.desc(), Collection.created_at.desc())
                    .limit(20)
                )
            ).scalars().all()
        )
        return user, boards

    # ── write operations ──────────────────────────────────────────────────────

    async def create_board(
        self,
        user: User,
        title: str,
        description: str,
        visibility: str,
        layout_config: dict | None = None,
    ) -> Collection:
        board = Collection(
            owner_user_id=user.id,
            title=title,
            description=description,
            visibility=visibility,
            layout_config=layout_config or {"mode": "swim-lane", "lanes": []},
        )
        self.db.add(board)
        await self.db.commit()
        await self.db.refresh(board)
        return board

    async def add_source_to_board(
        self,
        board_id: str,
        user: User,
        source_url: str | None,
        note: str,
        lane: str,
    ) -> CollectionItem:
        board = await self.get_board_for_owner(board_id, user)
        if board is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")

        if not source_url:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_url required")

        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_or_create_default(user)

        source = Source(
            id=str(uuid.uuid4()),
            owner_user_id=user.id,
            type="web_page",
            raw_url=source_url,
            title=source_url[:200],
        )
        self.db.add(source)
        await self.db.flush()

        item = CollectionItem(
            collection_id=board.id,
            source_id=source.id,
            added_by=user.id,
            note=note,
            lane=lane,
            position=len(board.items),
        )
        self.db.add(item)
        await self.db.flush()

        # Dispatch ingestion
        redis = await get_redis()
        await redis.xadd(
            STREAM_KEY,
            {
                "source_id": source.id,
                "user_id": user.id,
                "kb_id": kb.id,
                "vector_namespace": kb.vector_namespace,
                "upload": "0",
            },
        )

        await self.db.commit()
        return item

    async def fork_board(
        self,
        board_id: str,
        user: User,
        new_title: str,
        visibility: str = "private",
    ) -> Collection:
        original = await self.get_public_board(board_id)
        if original is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found or not public")

        new_lineage = build_fork_lineage(original.fork_lineage or [], original.id)

        # New collection (board)
        fork = Collection(
            owner_user_id=user.id,
            title=new_title,
            description=original.description,
            visibility=visibility,
            forked_from_id=original.id,
            fork_lineage=new_lineage,
            layout_config=original.layout_config,
        )
        self.db.add(fork)
        await self.db.flush()

        # Increment original's fork_count
        original.fork_count = (original.fork_count or 0) + 1

        # Create a dedicated KB for the fork
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_or_create_default(user)

        redis = await get_redis()

        for orig_item in original.items:
            orig_source = orig_item.source

            # Create a new Source record (new id → dedup keyed on (hash, source_id)
            # will produce fresh chunks stamped with the fork KB's namespace)
            new_source = Source(
                id=str(uuid.uuid4()),
                owner_user_id=user.id,
                type=orig_source.type,
                raw_url=orig_source.raw_url,
                storage_key=orig_source.storage_key,
                title=orig_source.title,
                description=orig_source.description,
                metadata_=orig_source.metadata_,
            )
            self.db.add(new_source)
            await self.db.flush()

            item = CollectionItem(
                collection_id=fork.id,
                source_id=new_source.id,
                added_by=user.id,
                note=orig_item.note,
                lane=orig_item.lane,
                position=orig_item.position,
            )
            self.db.add(item)
            await self.db.flush()

            is_upload = orig_source.storage_key is not None and orig_source.raw_url is None
            await redis.xadd(
                STREAM_KEY,
                {
                    "source_id": new_source.id,
                    "user_id": user.id,
                    "kb_id": kb.id,
                    "vector_namespace": kb.vector_namespace,
                    "upload": "1" if is_upload else "0",
                },
            )

        await self.db.commit()
        await self.db.refresh(fork)
        return fork

    async def generate_board_summary(self, board_id: str, user: User) -> str:
        board = await self.get_board_for_owner(board_id, user)
        if board is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")

        source_lines = "\n".join(
            f"  - {item.source.title}: {item.note or item.source.description[:100]}"
            for item in board.items
            if item.source
        )
        prompt = _SUMMARY_PROMPT.format(
            title=board.title,
            description=board.description or "(none)",
            count=len(board.items),
            source_list=source_lines or "  (no sources yet)",
        )

        from app.domains.generation.ollama import generate

        summary = await generate(prompt)
        board.ai_summary = summary.strip()
        await self.db.commit()
        return board.ai_summary

    async def update_board_embedding(self, board_id: str) -> None:
        """Recompute the board's centroid embedding from all its sources' chunks."""
        stmt = (
            select(Chunk.embedding)
            .join(Source, Chunk.source_id == Source.id)
            .join(CollectionItem, CollectionItem.source_id == Source.id)
            .where(
                CollectionItem.collection_id == board_id,
                Chunk.embedding.is_not(None),
                Chunk.is_overlap == False,  # noqa: E712
            )
        )
        rows = (await self.db.execute(stmt)).all()
        embeddings = [list(row[0]) for row in rows if row[0] is not None]
        if not embeddings:
            return

        dim = len(embeddings[0])
        centroid = [mean(emb[i] for emb in embeddings) for i in range(dim)]

        board = await self.db.get(Collection, board_id)
        if board:
            board.board_embedding = centroid
            await self.db.commit()
