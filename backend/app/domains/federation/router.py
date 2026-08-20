from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.federation.service import FederationService
from app.models.user import User
from app.schemas.federation import FeedOut

router = APIRouter(tags=["federation"])


@router.post(
    "/kbs/{kb_id}/federation",
    response_model=FeedOut,
    status_code=201,
    summary="Enable (or return) the KB's bundle feed — owner only; the slug is a capability",
)
async def enable_feed(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FeedOut:
    feed = await FederationService(db).enable_feed(kb_id, user)
    return FeedOut.model_validate(feed)


@router.get(
    "/kbs/{kb_id}/federation",
    response_model=FeedOut | None,
    summary="The KB's feed if enabled (owner only; null otherwise)",
)
async def get_feed(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FeedOut | None:
    feed = await FederationService(db).get_feed(kb_id, user)
    return FeedOut.model_validate(feed) if feed else None


@router.delete(
    "/kbs/{kb_id}/federation",
    status_code=204,
    summary="Revoke the KB's feed (re-enable mints a new slug — rotation)",
)
async def revoke_feed(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await FederationService(db).revoke_feed(kb_id, user)


# ── Unauthenticated capability endpoints (docs/23, OQ-95) ─────────────────────


@router.get("/federation/{slug}/meta", summary="Feed metadata (capability access — no auth)")
async def feed_meta(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    return await FederationService(db).serve_meta(slug)


@router.get("/federation/{slug}", summary="Feed bundle (capability access — no auth)")
async def feed_bundle(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    return await FederationService(db).serve_bundle(slug)


# ── Subscriptions (docs/23, OQ-96/97/98) ──────────────────────────────────────

from app.schemas.federation import SubscribeRequest, SubscriptionOut, SyncResultOut  # noqa: E402


@router.post(
    "/federation/subscriptions",
    response_model=SubscriptionOut,
    status_code=201,
    summary="Subscribe to a remote bundle feed — creates a private mirror KB",
)
async def subscribe(
    req: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubscriptionOut:
    sub = await FederationService(db).subscribe(req.feed_url, user)
    return SubscriptionOut.model_validate(sub)


@router.get(
    "/kbs/{kb_id}/subscription",
    response_model=SubscriptionOut | None,
    summary="The KB's mirror record if it is a subscription mirror (null otherwise)",
)
async def get_subscription_for_kb(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubscriptionOut | None:
    sub = await FederationService(db).get_for_kb(kb_id, user)
    return SubscriptionOut.model_validate(sub) if sub else None


@router.post(
    "/federation/subscriptions/{sub_id}/sync",
    response_model=SyncResultOut,
    summary="Re-sync a mirror from its feed (meta-first; full replace on change)",
)
async def sync_subscription(
    sub_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncResultOut:
    result = await FederationService(db).sync(sub_id, user)
    return SyncResultOut(**result)


@router.delete(
    "/federation/subscriptions/{sub_id}",
    status_code=204,
    summary="Unsubscribe — the KB stays and becomes an ordinary local KB",
)
async def unsubscribe(
    sub_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await FederationService(db).unsubscribe(sub_id, user)
