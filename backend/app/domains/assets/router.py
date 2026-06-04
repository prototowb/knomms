from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.assets.service import AssetService
from app.models.user import User
from app.schemas.asset import (
    AddVersionRequest,
    AssetOut,
    AssetSummary,
    AssetVersionOut,
    CreateAssetRequest,
    ProjectionOut,
    ProjectVersionRequest,
)

router = APIRouter(tags=["assets"])


def _asset_to_out(asset) -> AssetOut:
    return AssetOut(
        id=asset.id,
        title=asset.title,
        description=asset.description,
        asset_type=asset.asset_type,
        visibility=asset.visibility,
        fork_count=asset.fork_count,
        forked_from_id=asset.forked_from_id,
        fork_lineage=asset.fork_lineage or [],
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        owner=asset.owner if hasattr(asset, "owner") and asset.owner else None,
        versions=[AssetVersionOut.model_validate(v) for v in (asset.versions or [])],
    )


def _asset_to_summary(asset) -> AssetSummary:
    version_count = len(asset.versions) if hasattr(asset, "versions") and asset.versions else 0
    return AssetSummary(
        id=asset.id,
        title=asset.title,
        description=asset.description,
        asset_type=asset.asset_type,
        visibility=asset.visibility,
        fork_count=asset.fork_count,
        created_at=asset.created_at,
        owner=asset.owner if hasattr(asset, "owner") and asset.owner else None,
        version_count=version_count,
    )


@router.get("/assets", response_model=list[AssetSummary], summary="List/search assets visible to the current user")
async def list_assets(
    asset_type: str | None = Query(None),
    visibility: str | None = Query(None, pattern="^(private|team|public)$"),
    q: str | None = Query(None, min_length=2, description="Full-text search across title, description, rationale"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AssetSummary]:
    svc = AssetService(db)
    assets = await svc.list_assets(user, asset_type=asset_type, visibility_filter=visibility, q=q, limit=limit, offset=offset)
    return [_asset_to_summary(a) for a in assets]


@router.post("/assets", response_model=AssetOut, status_code=201, summary="Create a new asset")
async def create_asset(
    req: CreateAssetRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    svc = AssetService(db)
    asset = await svc.create_asset(user, req.title, req.description, req.asset_type, req.visibility)
    # Re-fetch with relationships loaded
    asset = await svc.get_asset(asset.id, user)
    return _asset_to_out(asset)


@router.get("/assets/{asset_id}", response_model=AssetOut, summary="Get an asset with all versions")
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, user)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return _asset_to_out(asset)


@router.post(
    "/assets/{asset_id}/versions",
    response_model=AssetVersionOut,
    status_code=201,
    summary="Add a new version to an asset (deduped by content hash)",
)
async def add_version(
    asset_id: str,
    req: AddVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetVersionOut:
    svc = AssetService(db)
    version = await svc.add_version(
        asset_id, user, req.content, req.rationale, req.tags or [], req.model_pin
    )
    return AssetVersionOut.model_validate(version)


@router.post(
    "/assets/{asset_id}/versions/{version_num}/project",
    response_model=ProjectionOut,
    status_code=201,
    summary="Project an asset version into a KB as a prompt_asset source (deduped by version+KB)",
)
async def project_version(
    asset_id: str,
    version_num: int,
    req: ProjectVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectionOut:
    svc = AssetService(db)
    projection = await svc.project_version(asset_id, version_num, req.kb_id, user)
    return ProjectionOut.model_validate(projection)


@router.post(
    "/assets/{asset_id}/versions/{version_num}/deprecate",
    response_model=AssetVersionOut,
    summary="Mark a version as deprecated",
)
async def deprecate_version(
    asset_id: str,
    version_num: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetVersionOut:
    svc = AssetService(db)
    version = await svc.deprecate_version(asset_id, version_num, user)
    return AssetVersionOut.model_validate(version)
