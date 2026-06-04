"""Harness service — create, fork, get, list, add/swap asset versions."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.curation.types import build_fork_lineage
from app.models.asset import AssetVersion, Harness, HarnessAsset
from app.models.user import User

VISIBILITIES = frozenset({"private", "team", "public"})


class HarnessService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── read operations ───────────────────────────────────────────────────────

    async def get_harness(self, harness_id: str, user: User) -> Harness | None:
        stmt = (
            select(Harness)
            .where(
                Harness.id == harness_id,
                or_(
                    Harness.owner_user_id == user.id,
                    Harness.visibility.in_(("team", "public")),
                ),
            )
            .options(
                selectinload(Harness.assets),
                selectinload(Harness.owner),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_harnesses(
        self,
        user: User,
        visibility_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Harness]:
        base_predicate = or_(
            Harness.owner_user_id == user.id,
            Harness.visibility.in_(("team", "public")),
        )

        if visibility_filter == "private":
            stmt = select(Harness).where(
                Harness.owner_user_id == user.id,
                Harness.visibility == "private",
            )
        elif visibility_filter in ("team", "public"):
            stmt = select(Harness).where(base_predicate, Harness.visibility == visibility_filter)
        else:
            stmt = select(Harness).where(base_predicate)

        stmt = (
            stmt.options(selectinload(Harness.assets), selectinload(Harness.owner))
            .order_by(Harness.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── write operations ──────────────────────────────────────────────────────

    async def create_harness(
        self,
        user: User,
        title: str,
        description: str,
        visibility: str,
    ) -> Harness:
        if visibility not in VISIBILITIES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"visibility must be one of: {sorted(VISIBILITIES)}",
            )

        harness = Harness(
            owner_user_id=user.id,
            title=title,
            description=description,
            visibility=visibility,
        )
        self.db.add(harness)
        await self.db.commit()
        await self.db.refresh(harness)
        return harness

    async def fork_harness(
        self,
        harness_id: str,
        user: User,
        new_title: str,
        visibility: str = "private",
    ) -> Harness:
        original = (
            await self.db.execute(
                select(Harness)
                .where(
                    Harness.id == harness_id,
                    or_(
                        Harness.owner_user_id == user.id,
                        Harness.visibility.in_(("team", "public")),
                    ),
                )
                .options(selectinload(Harness.assets))
            )
        ).scalar_one_or_none()

        if original is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found or not accessible")

        new_lineage = build_fork_lineage(original.fork_lineage or [], original.id)

        fork = Harness(
            owner_user_id=user.id,
            title=new_title,
            description=original.description,
            visibility=visibility,
            forked_from_id=original.id,
            fork_lineage=new_lineage,
        )
        self.db.add(fork)
        await self.db.flush()

        original.fork_count = (original.fork_count or 0) + 1

        # Copy HarnessAsset rows — new IDs, same roles/positions/version references
        for slot in original.assets:
            new_slot = HarnessAsset(
                id=str(uuid.uuid4()),
                harness_id=fork.id,
                asset_version_id=slot.asset_version_id,
                role=slot.role,
                position=slot.position,
            )
            self.db.add(new_slot)

        await self.db.commit()
        await self.db.refresh(fork)
        return fork

    async def add_asset_version(
        self,
        harness_id: str,
        user: User,
        asset_version_id: str,
        role: str,
        position: int = 0,
    ) -> HarnessAsset:
        harness = await self.db.get(Harness, harness_id)
        if harness is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
        if harness.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the harness owner")

        # Verify the asset version exists
        av = await self.db.get(AssetVersion, asset_version_id)
        if av is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset version not found")

        slot = HarnessAsset(
            harness_id=harness_id,
            asset_version_id=asset_version_id,
            role=role,
            position=position,
        )
        self.db.add(slot)
        await self.db.commit()
        await self.db.refresh(slot)
        return slot

    async def swap_asset_version(
        self,
        harness_id: str,
        role: str,
        user: User,
        new_asset_version_id: str,
    ) -> HarnessAsset:
        harness = await self.db.get(Harness, harness_id)
        if harness is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
        if harness.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the harness owner")

        # Verify the new asset version exists
        av = await self.db.get(AssetVersion, new_asset_version_id)
        if av is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset version not found")

        slot_stmt = select(HarnessAsset).where(
            HarnessAsset.harness_id == harness_id,
            HarnessAsset.role == role,
        )
        slot = (await self.db.execute(slot_stmt)).scalar_one_or_none()
        if slot is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"No asset slot with role '{role}' in this harness",
            )

        slot.asset_version_id = new_asset_version_id
        await self.db.commit()
        await self.db.refresh(slot)
        return slot
