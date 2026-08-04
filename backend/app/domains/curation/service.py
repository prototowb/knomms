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

    async def get_similar_boards(self, board_id: str, limit: int = 5) -> list[Collection]:
        """Return public boards whose board_embedding is closest to the given board.

        Uses the source board's stored centroid vector directly — no Ollama call needed.
        Excludes the source board itself and boards without an embedding.
        """
        board = await self.db.get(Collection, board_id)
        if board is None or board.board_embedding is None:
            return []

        stmt = (
            select(
                Collection,
                Collection.board_embedding.cosine_distance(board.board_embedding).label("distance"),
            )
            .where(
                Collection.id != board_id,
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

    async def list_my_boards(self, user: User) -> list[Collection]:
        result = await self.db.execute(
            select(Collection)
            .where(Collection.owner_user_id == user.id)
            .options(selectinload(Collection.items))
            .order_by(Collection.updated_at.desc())
        )
        return list(result.scalars().all())

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
        await self.db.flush()

        # Every board has its own isolated KB so its sources can be queried
        # independently — the same invariant enforced for fork_board.
        # The KB mirrors the board's visibility (KC-058): a public board is
        # useless if readers can't query its dedicated KB.
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.create(user, title=f"Board: {title}", visibility=visibility)
        from app.models.knowledge_base import knowledge_base_collection
        await self.db.execute(
            knowledge_base_collection.insert().values(kb_id=kb.id, collection_id=board.id)
        )

        await self.db.commit()
        await self.db.refresh(board)
        return board

    async def _resolve_board_kb(self, board: Collection, user: User):
        """Return the board's dedicated KnowledgeBase, creating and linking one if missing."""
        from app.models.knowledge_base import KnowledgeBase, knowledge_base_collection

        kb = (await self.db.execute(
            select(KnowledgeBase)
            .join(knowledge_base_collection, knowledge_base_collection.c.kb_id == KnowledgeBase.id)
            .where(knowledge_base_collection.c.collection_id == board.id)
            .limit(1)
        )).scalar_one_or_none()

        if kb is None:
            kb_svc = KnowledgeBaseService(self.db)
            kb = await kb_svc.create(
                user, title=f"Board: {board.title}", visibility=board.visibility
            )
            from app.models.knowledge_base import knowledge_base_collection as kbc
            await self.db.execute(
                kbc.insert().values(kb_id=kb.id, collection_id=board.id)
            )
        return kb

    async def sync_board_kb_visibility(self, board: Collection, user: User) -> None:
        """Mirror the board's visibility onto its dedicated KB (KC-058) —
        a public board is useless if readers can't query its KB. Does not
        commit; the caller owns the transaction."""
        kb = await self._resolve_board_kb(board, user)
        kb.visibility = board.visibility

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

        kb = await self._resolve_board_kb(board, user)

        source = Source(
            id=str(uuid.uuid4()),
            owner_user_id=user.id,
            type="web_page",
            raw_url=source_url,
            title=source_url[:200],
            kb_id=kb.id,
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

        redis = await get_redis()
        await redis.xadd(STREAM_KEY, {
            "source_id": source.id,
            "user_id": user.id,
            "kb_id": kb.id,
            "vector_namespace": kb.vector_namespace,
            "upload": "0",
        })

        await self.db.commit()
        return await self._reload_item(item.id)

    async def add_asset_to_board(
        self,
        board_id: str,
        user: User,
        asset_id: str,
        version_num: int,
        note: str,
        lane: str,
    ) -> CollectionItem:
        """Project an asset version onto a board as a prompt_asset CollectionItem.

        Mirrors add_source_to_board + AssetService.project_version rather than
        calling the latter (it commits internally — same precedent as
        add_file_to_board vs IngestionService.submit_file). Re-adding a version
        already projected into the board's KB reuses the existing Source.
        """
        from sqlalchemy.exc import IntegrityError

        from app.models.asset import Asset, AssetSourceProjection, AssetVersion

        board = await self.get_board_for_owner(board_id, user)
        if board is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")

        asset = await self.db.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
        if asset.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the asset owner")

        version = (await self.db.execute(
            select(AssetVersion).where(
                AssetVersion.asset_id == asset_id,
                AssetVersion.version_num == version_num,
            )
        )).scalar_one_or_none()
        if version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Version not found")

        kb = await self._resolve_board_kb(board, user)
        # Capture scalars before any rollback — expired ORM attributes cannot be
        # lazily refreshed on an async session.
        user_id = user.id
        kb_id, vector_namespace = kb.id, kb.vector_namespace
        version_id, version_content = version.id, version.content
        asset_title, asset_description = asset.title, asset.description

        source_id = str(uuid.uuid4())
        source = Source(
            id=source_id,
            owner_user_id=user.id,
            type="prompt_asset",
            title=f"{asset_title} v{version_num}",
            description=asset_description,
            kb_id=kb_id,
            ingestion_status="pending",
        )
        self.db.add(source)
        await self.db.flush()

        projection = AssetSourceProjection(
            asset_version_id=version_id,
            kb_id=kb_id,
            source_id=source_id,
            owner_user_id=user.id,
        )
        self.db.add(projection)

        needs_ingestion = True
        try:
            await self.db.flush()
        except IntegrityError:
            # Version already projected into this board's KB — reuse that Source
            # instead of erroring; the user's intent is "put this on my board".
            # Re-select the board directly (by captured user_id, not the expired
            # `user` instance) — every ORM object in the session expired on rollback.
            await self.db.rollback()
            board = (await self.db.execute(
                select(Collection)
                .where(Collection.id == board_id, Collection.owner_user_id == user_id)
                .options(selectinload(Collection.items))
            )).scalar_one()
            existing = (await self.db.execute(
                select(AssetSourceProjection).where(
                    AssetSourceProjection.asset_version_id == version_id,
                    AssetSourceProjection.kb_id == kb_id,
                )
            )).scalar_one()
            source_id = existing.source_id
            needs_ingestion = False

        item = CollectionItem(
            collection_id=board.id,
            source_id=source_id,
            added_by=user_id,
            note=note,
            lane=lane,
            position=len(board.items),
        )
        self.db.add(item)
        await self.db.flush()

        if needs_ingestion:
            redis = await get_redis()
            await redis.setex(f"upload:{source_id}", 3600, version_content.encode("utf-8"))
            await redis.xadd(STREAM_KEY, {
                "source_id": source_id,
                "user_id": user_id,
                "kb_id": kb_id,
                "vector_namespace": vector_namespace,
                "upload": "1",
            })

        await self.db.commit()
        return await self._reload_item(item.id)

    async def add_file_to_board(
        self,
        board_id: str,
        user: User,
        file,  # fastapi.UploadFile — typed as Any to avoid importing fastapi in this module
        note: str,
        lane: str,
    ) -> CollectionItem:
        """Accept a file upload and ingest it into the board's dedicated KB."""
        board = await self.get_board_for_owner(board_id, user)
        if board is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")

        filename: str = file.filename or "upload"
        suffix = filename.rsplit(".", 1)[-1].lower()
        source_type = {"pdf": "pdf", "docx": "plain_text", "doc": "plain_text",
                       "txt": "plain_text", "md": "plain_text", "epub": "epub"}.get(suffix, "plain_text")

        content: bytes = await file.read()
        if len(content) > 200 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 200MB limit")

        kb = await self._resolve_board_kb(board, user)

        source_id = str(uuid.uuid4())
        storage_key = f"raw/{user.id}/{source_id}/{filename}"

        source = Source(
            id=source_id,
            owner_user_id=user.id,
            type=source_type,
            storage_key=storage_key,
            title=filename,
            kb_id=kb.id,
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

        # Write to MinIO for durable storage, then also cache in Redis for fast
        # worker pickup (same dual-write pattern as IngestionService.submit_file).
        from app.core.config import settings as _settings
        from app.core.storage import write_object
        await write_object(_settings.minio_bucket, storage_key, content)
        redis = await get_redis()
        await redis.setex(f"upload:{source_id}", 3600, content)
        await redis.xadd(STREAM_KEY, {
            "source_id": source.id,
            "user_id": user.id,
            "kb_id": kb.id,
            "vector_namespace": kb.vector_namespace,
            "upload": "1",
        })

        await self.db.commit()
        return await self._reload_item(item.id)

    async def _reload_item(self, item_id: str) -> "CollectionItem":
        """Re-fetch a CollectionItem with its source relationship loaded."""
        stmt = (
            select(CollectionItem)
            .where(CollectionItem.id == item_id)
            .options(selectinload(CollectionItem.source))
        )
        return (await self.db.execute(stmt)).scalar_one()

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

        # Create a fresh KB with its own isolated vector_namespace.
        # Using get_or_create_default would share the user's default namespace
        # across all forks, making cross-fork queries bleed — each fork must
        # have its own namespace so retrieval isolation holds.
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.create(user, title=new_title, visibility=visibility)

        # Link the fork Collection to its KB via the join table
        from app.models.knowledge_base import knowledge_base_collection
        await self.db.execute(
            knowledge_base_collection.insert().values(
                kb_id=kb.id, collection_id=fork.id
            )
        )

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
                kb_id=kb.id,  # stamp fork KB so GET /v1/kbs/{id}/sources works
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

    async def request_board_summary(self, board_id: str, user: User) -> Collection:
        """Mark a board summary as queued for async generation (KC-030).

        Raises 404/422 synchronously so the client gets immediate feedback;
        the actual Ollama call happens in the board.summary.jobs worker.
        """
        board = await self.get_board_for_owner(board_id, user)
        if board is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
        if not board.items:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Board has no sources to summarize",
            )
        if board.summary_status == "generating":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="A summary is already being generated for this board",
            )

        board.summary_status = "generating"
        await self.db.commit()
        await self.db.refresh(board)
        return board

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
