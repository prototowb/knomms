"""Harness service — create, fork, get, list, add/swap asset versions, submit eval."""

import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import get_redis
from app.domains.curation.types import build_fork_lineage
from app.domains.organisations.predicates import has_grant, readable_clause
from app.models.asset import AssetVersion, EvalCase, EvalRun, Harness, HarnessAsset
from app.models.user import User

_EVAL_STREAM_KEY = "eval.jobs"

VISIBILITIES = frozenset({"private", "team", "public"})

EVAL_PROVIDERS = frozenset({"ollama", "anthropic"})


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
                    readable_clause(Harness, "harness", user),
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
            readable_clause(Harness, "harness", user),
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

    async def update_harness(
        self,
        harness_id: str,
        user: User,
        title: str | None = None,
        description: str | None = None,
        visibility: str | None = None,
    ) -> Harness:
        """Owner-only metadata update — None means unchanged (boards precedent)."""
        harness = await self.db.get(Harness, harness_id)
        if harness is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
        if harness.owner_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the harness owner")

        if title is not None:
            harness.title = title
        if description is not None:
            harness.description = description
        if visibility is not None:
            if visibility not in VISIBILITIES:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"visibility must be one of: {sorted(VISIBILITIES)}",
                )
            harness.visibility = visibility

        await self.db.commit()
        return await self.get_harness(harness_id, user)

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
                        readable_clause(Harness, "harness", user),
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
        # Slots and evals are the harness's OQ-18 editor surface
        if harness.owner_user_id != user.id and not await has_grant(
            self.db, "harness", harness_id, user, permissions=("editor",)
        ):
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

    async def submit_eval(
        self,
        harness_id: str,
        user: User,
        model: str,
        provider: str = "ollama",
    ) -> EvalRun:
        if provider not in EVAL_PROVIDERS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"provider must be one of: {sorted(EVAL_PROVIDERS)}",
            )
        harness = await self.db.get(Harness, harness_id)
        if harness is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
        # Slots and evals are the harness's OQ-18 editor surface
        if harness.owner_user_id != user.id and not await has_grant(
            self.db, "harness", harness_id, user, permissions=("editor",)
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not the harness owner")

        if provider == "anthropic":
            await self._validate_cloud_eval(harness_id, model)
        else:
            # Validate model is available locally — zero-external-cost invariant
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                    resp.raise_for_status()
                    available = [m["name"] for m in resp.json().get("models", [])]
            except Exception as exc:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not reach Ollama to validate model: {exc}",
                )

            if model not in available:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Model '{model}' is not available locally. Available: {available}",
                )

        eval_run = EvalRun(
            harness_id=harness_id,
            triggered_by=user.id,
            model_pin=model,
            provider=provider,
            status="queued",
        )
        self.db.add(eval_run)
        await self.db.commit()
        await self.db.refresh(eval_run)

        redis = await get_redis()
        await redis.xadd(_EVAL_STREAM_KEY, {
            "run_id": eval_run.id,
            "harness_id": harness_id,
        })

        return eval_run

    async def _validate_cloud_eval(self, harness_id: str, model: str) -> None:
        """Pre-flight for provider=anthropic (docs/11 OQ-24/25): opt-in gate,
        live model check, and case-count cap — refused BEFORE any spend."""
        from app.domains.generation import cloud

        if not cloud.is_enabled():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cloud eval is not enabled on this instance "
                "(set CLOUD_EVAL_ENABLED and ANTHROPIC_API_KEY)",
            )
        try:
            available = await cloud.list_models()
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not reach the cloud provider to validate model: {exc}",
            )
        if model not in available:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Model '{model}' is not available from the provider",
            )

        # Case-count cap — bounded worst-case spend per click (OQ-25)
        suite_slot = (
            await self.db.execute(
                select(HarnessAsset).where(
                    HarnessAsset.harness_id == harness_id,
                    HarnessAsset.role == "eval_suite",
                )
            )
        ).scalar_one_or_none()
        if suite_slot is not None:
            case_count = (
                await self.db.execute(
                    select(func.count(EvalCase.id)).where(
                        EvalCase.asset_version_id == suite_slot.asset_version_id
                    )
                )
            ).scalar() or 0
            if case_count > settings.cloud_eval_max_cases:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Eval suite has {case_count} cases — cloud runs are "
                    f"capped at {settings.cloud_eval_max_cases} (CLOUD_EVAL_MAX_CASES)",
                )

    async def list_eval_runs(self, harness_id: str, user: User, limit: int = 20) -> list[EvalRun]:
        """List a harness's eval runs, newest first. Owner or editor grantee
        (an editor can submit evals, so they must be able to see them) — still
        404 for everyone else so run history doesn't leak through public/team
        harnesses."""
        harness = await self.db.get(Harness, harness_id)
        if harness is None or (
            harness.owner_user_id != user.id
            and not await has_grant(
                self.db, "harness", harness_id, user, permissions=("editor",)
            )
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")

        stmt = (
            select(EvalRun)
            .where(EvalRun.harness_id == harness_id)
            .order_by(EvalRun.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_eval_run(self, run_id: str, user: User) -> EvalRun | None:
        eval_run = await self.db.get(EvalRun, run_id)
        if eval_run is None:
            return None
        # Harness owner or editor grantee (matches list_eval_runs)
        harness = await self.db.get(Harness, eval_run.harness_id)
        if harness is None or (
            harness.owner_user_id != user.id
            and not await has_grant(
                self.db, "harness", harness.id, user, permissions=("editor",)
            )
        ):
            return None
        return eval_run

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
        # Slots and evals are the harness's OQ-18 editor surface
        if harness.owner_user_id != user.id and not await has_grant(
            self.db, "harness", harness_id, user, permissions=("editor",)
        ):
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
