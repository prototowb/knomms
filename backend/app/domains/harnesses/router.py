from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.harnesses.service import HarnessService
from app.models.user import User
from app.schemas.harness import (
    AddAssetVersionRequest,
    CreateHarnessRequest,
    ForkHarnessRequest,
    HarnessAssetOut,
    HarnessOut,
    HarnessSummary,
    SwapAssetVersionRequest,
)

router = APIRouter(tags=["harnesses"])


def _harness_to_out(harness) -> HarnessOut:
    return HarnessOut(
        id=harness.id,
        title=harness.title,
        description=harness.description,
        visibility=harness.visibility,
        fork_count=harness.fork_count,
        forked_from_id=harness.forked_from_id,
        fork_lineage=harness.fork_lineage or [],
        created_at=harness.created_at,
        updated_at=harness.updated_at,
        owner=harness.owner if hasattr(harness, "owner") and harness.owner else None,
        assets=[HarnessAssetOut.model_validate(s) for s in (harness.assets or [])],
    )


def _harness_to_summary(harness) -> HarnessSummary:
    asset_count = len(harness.assets) if hasattr(harness, "assets") and harness.assets else 0
    return HarnessSummary(
        id=harness.id,
        title=harness.title,
        description=harness.description,
        visibility=harness.visibility,
        fork_count=harness.fork_count,
        created_at=harness.created_at,
        owner=harness.owner if hasattr(harness, "owner") and harness.owner else None,
        asset_count=asset_count,
    )


@router.get("/harnesses", response_model=list[HarnessSummary], summary="List harnesses visible to the current user")
async def list_harnesses(
    visibility: str | None = Query(None, pattern="^(private|team|public)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HarnessSummary]:
    svc = HarnessService(db)
    harnesses = await svc.list_harnesses(user, visibility_filter=visibility, limit=limit, offset=offset)
    return [_harness_to_summary(h) for h in harnesses]


@router.post("/harnesses", response_model=HarnessOut, status_code=201, summary="Create a new harness")
async def create_harness(
    req: CreateHarnessRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessOut:
    svc = HarnessService(db)
    harness = await svc.create_harness(user, req.title, req.description, req.visibility)
    harness = await svc.get_harness(harness.id, user)
    return _harness_to_out(harness)


@router.get("/harnesses/{harness_id}", response_model=HarnessOut, summary="Get a harness with its asset slots")
async def get_harness(
    harness_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessOut:
    svc = HarnessService(db)
    harness = await svc.get_harness(harness_id, user)
    if harness is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
    return _harness_to_out(harness)


@router.post(
    "/harnesses/{harness_id}/fork",
    response_model=HarnessOut,
    status_code=201,
    summary="Fork a harness (copies all asset slots)",
)
async def fork_harness(
    harness_id: str,
    req: ForkHarnessRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessOut:
    svc = HarnessService(db)
    fork = await svc.fork_harness(harness_id, user, req.new_title, req.visibility)
    fork = await svc.get_harness(fork.id, user)
    return _harness_to_out(fork)


@router.post(
    "/harnesses/{harness_id}/assets",
    response_model=HarnessAssetOut,
    status_code=201,
    summary="Add an asset version to a harness by role",
)
async def add_asset_version(
    harness_id: str,
    req: AddAssetVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessAssetOut:
    svc = HarnessService(db)
    slot = await svc.add_asset_version(harness_id, user, req.asset_version_id, req.role, req.position)
    return HarnessAssetOut.model_validate(slot)


@router.put(
    "/harnesses/{harness_id}/assets/{role}",
    response_model=HarnessAssetOut,
    summary="Swap the asset version for a given role",
)
async def swap_asset_version(
    harness_id: str,
    role: str,
    req: SwapAssetVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessAssetOut:
    svc = HarnessService(db)
    slot = await svc.swap_asset_version(harness_id, role, user, req.new_asset_version_id)
    return HarnessAssetOut.model_validate(slot)
