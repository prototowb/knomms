"""Asset service — create assets, version management, list, deprecate, project."""

import hashlib
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.models.asset import Asset, AssetSourceProjection, AssetVersion
from app.models.source import Source
from app.models.user import User

_INGESTION_STREAM_KEY = "ingestion.jobs"

ASSET_TYPES = frozenset({"system_prompt", "few_shot_set", "eval_suite", "chain_spec", "tool_spec"})
VISIBILITIES = frozenset({"private", "team", "public"})


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest of the UTF-8 encoded content string."""
    return hashlib.sha256(content.encode()).hexdigest()


def next_version_num(existing_nums: list[int]) -> int:
    """Return the next version number (max + 1, or 1 if no versions exist)."""
    return max(existing_nums) + 1 if existing_nums else 1


class AssetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── read operations ───────────────────────────────────────────────────────

    async def get_asset(self, asset_id: str, user: User) -> Asset | None:
        stmt = (
            select(Asset)
            .where(
                Asset.id == asset_id,
                or_(
                    Asset.owner_user_id == user.id,
                    Asset.visibility.in_(("team", "public")),
                ),
            )
            .options(
                selectinload(Asset.versions),
                selectinload(Asset.owner),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assets(
        self,
        user: User,
        asset_type: str | None = None,
        visibility_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Asset]:
        # Base access control: own assets + team/public assets
        base_predicate = or_(
            Asset.owner_user_id == user.id,
            Asset.visibility.in_(("team", "public")),
        )

        # Narrow by visibility filter without leaking others' private assets.
        # ?visibility=private → only own private assets (owner + private)
        if visibility_filter == "private":
            visibility_predicate = (
                Asset.owner_user_id == user.id,
                Asset.visibility == "private",
            )
            stmt = select(Asset).where(*visibility_predicate)
        elif visibility_filter in ("team", "public"):
            stmt = select(Asset).where(base_predicate, Asset.visibility == visibility_filter)
        else:
            stmt = select(Asset).where(base_predicate)

        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type)

        stmt = (
            stmt.options(selectinload(Asset.versions), selectinload(Asset.owner))
            .order_by(Asset.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── write operations ──────────────────────────────────────────────────────

    async def create_asset(
        self,
        user: User,
        title: str,
        description: str,
        asset_type: str,
        visibility: str,
    ) -> Asset:
        if asset_type not in ASSET_TYPES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"asset_type must be one of: {sorted(ASSET_TYPES)}",
            )
        if visibility not in VISIBILITIES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"visibility must be one of: {sorted(VISIBILITIES)}",
            )

        asset = Asset(
            owner_user_id=user.id,
            title=title,
            description=description,
            asset_type=asset_type,
            visibility=visibility,
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def add_version(
        self,
        asset_id: str,
        user: User,
        content: str,
        rationale: str = "",
        tags: list[str] | None = None,
        model_pin: str | None = None,
    ) -> AssetVersion:
        asset = await self.db.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
        if asset.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the asset owner")

        content_hash = compute_content_hash(content)

        # Dedup: if this exact content already exists as a version, return it
        existing_stmt = select(AssetVersion).where(
            AssetVersion.asset_id == asset_id,
            AssetVersion.content_hash == content_hash,
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        # Compute the next version number scoped to this asset
        versions_stmt = select(AssetVersion.version_num).where(AssetVersion.asset_id == asset_id)
        existing_nums = list((await self.db.execute(versions_stmt)).scalars().all())
        version_num = next_version_num(existing_nums)

        version = AssetVersion(
            asset_id=asset_id,
            version_num=version_num,
            content=content,
            content_hash=content_hash,
            rationale=rationale,
            tags=tags or [],
            model_pin=model_pin,
            status="draft",
            created_by=user.id,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def project_version(
        self,
        asset_id: str,
        version_num: int,
        kb_id: str,
        user: User,
    ) -> AssetSourceProjection:
        """Project an asset version into a KB as a prompt_asset Source, then ingest it."""
        # Resolve asset and version
        asset = await self.db.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
        if asset.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the asset owner")

        version_stmt = select(AssetVersion).where(
            AssetVersion.asset_id == asset_id,
            AssetVersion.version_num == version_num,
        )
        version = (await self.db.execute(version_stmt)).scalar_one_or_none()
        if version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Version not found")

        # Verify the KB exists and belongs to the user
        from app.models.knowledge_base import KnowledgeBase
        kb = await self.db.get(KnowledgeBase, kb_id)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
        if kb.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the KB owner")

        # Create a Source record of type prompt_asset
        source_id = str(uuid.uuid4())
        source = Source(
            id=source_id,
            owner_user_id=user.id,
            type="prompt_asset",
            title=f"{asset.title} v{version_num}",
            description=asset.description,
            kb_id=kb_id,
            ingestion_status="pending",
        )
        self.db.add(source)
        await self.db.flush()

        projection = AssetSourceProjection(
            asset_version_id=version.id,
            kb_id=kb_id,
            source_id=source_id,
            owner_user_id=user.id,
        )
        self.db.add(projection)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="This asset version is already projected into the specified KB",
            )

        # Write content to Redis so the worker can read it without MinIO
        redis = await get_redis()
        content_bytes = version.content.encode("utf-8")
        await redis.setex(f"upload:{source_id}", 3600, content_bytes)

        # Push ingestion job — upload=1 so worker reads from Redis
        await redis.xadd(_INGESTION_STREAM_KEY, {
            "source_id": source_id,
            "user_id": user.id,
            "kb_id": kb_id,
            "vector_namespace": kb.vector_namespace,
            "upload": "1",
        })

        await self.db.commit()
        await self.db.refresh(projection)
        return projection

    async def deprecate_version(
        self,
        asset_id: str,
        version_num: int,
        user: User,
    ) -> AssetVersion:
        asset = await self.db.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
        if asset.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the asset owner")

        stmt = select(AssetVersion).where(
            AssetVersion.asset_id == asset_id,
            AssetVersion.version_num == version_num,
        )
        version = (await self.db.execute(stmt)).scalar_one_or_none()
        if version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Version not found")

        version.status = "deprecated"
        await self.db.commit()
        await self.db.refresh(version)
        return version
