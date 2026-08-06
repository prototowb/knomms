import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.harnesses.service import HarnessService
from app.models.user import User
from app.schemas.harness import (
    AddAssetVersionRequest,
    CreateHarnessRequest,
    EvalRunOut,
    ForkHarnessRequest,
    HarnessAssetOut,
    HarnessOut,
    HarnessSummary,
    SubmitEvalRequest,
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


from pydantic import BaseModel as _BaseModel


class UpdateHarnessRequest(_BaseModel):
    title: str | None = None
    description: str | None = None
    visibility: str | None = None


@router.patch("/harnesses/{harness_id}", response_model=HarnessOut, summary="Update harness metadata (owner only)")
async def update_harness(
    harness_id: str,
    req: UpdateHarnessRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HarnessOut:
    svc = HarnessService(db)
    harness = await svc.update_harness(
        harness_id, user, title=req.title, description=req.description, visibility=req.visibility
    )
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


@router.post(
    "/harnesses/{harness_id}/eval",
    response_model=EvalRunOut,
    status_code=202,
    summary="Submit an eval run for a harness (queues worker job; fails 422 if model not local)",
)
async def submit_eval(
    harness_id: str,
    req: SubmitEvalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvalRunOut:
    svc = HarnessService(db)
    eval_run = await svc.submit_eval(harness_id, user, req.model, provider=req.provider)
    return EvalRunOut.model_validate(eval_run)


@router.get(
    "/harnesses/{harness_id}/eval",
    response_model=list[EvalRunOut],
    summary="List a harness's eval runs, newest first (owner only)",
)
async def list_eval_runs(
    harness_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EvalRunOut]:
    svc = HarnessService(db)
    runs = await svc.list_eval_runs(harness_id, user, limit=limit)
    return [EvalRunOut.model_validate(r) for r in runs]


@router.get(
    "/harnesses/{harness_id}/eval/{run_id}",
    response_model=EvalRunOut,
    summary="Get the status and results of an eval run",
)
async def get_eval_run(
    harness_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvalRunOut:
    svc = HarnessService(db)
    eval_run = await svc.get_eval_run(run_id, user)
    if eval_run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Eval run not found")
    return EvalRunOut.model_validate(eval_run)


@router.get(
    "/harnesses/{harness_id}/eval/{run_id}/events",
    summary="SSE stream of eval progress events for a run",
)
async def eval_events(
    harness_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    svc = HarnessService(db)
    eval_run = await svc.get_eval_run(run_id, user)
    if eval_run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Eval run not found")

    async def _event_stream():
        # Use a fresh session — the request-scoped `db` dependency is cleaned up
        # once the route handler returns; StreamingResponse generators outlive that.
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import select as _select
        from app.models.asset import EvalRun as _EvalRun

        redis = await get_redis()
        offset = 0
        async with AsyncSessionLocal() as stream_db:
            while True:
                events = await redis.lrange(f"eval:events:{run_id}", offset, -1)
                for raw in events:
                    yield f"data: {raw}\n\n"
                    offset += 1

                if events:
                    last = json.loads(events[-1])
                    if last.get("type") in ("complete", "error"):
                        return

                # Check DB status in case worker died without writing a final event
                result = await stream_db.execute(
                    _select(_EvalRun.status).where(_EvalRun.id == run_id)
                )
                db_status = result.scalar_one_or_none()
                if db_status in ("completed", "failed") and not events:
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    return

                await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
