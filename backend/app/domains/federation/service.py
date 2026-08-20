"""Federation feeds & subscriptions (docs/23) — pull-based sharing over the
bundle-v1 wire format. Feeds are capability URLs (OQ-95): possession of the
slug grants read, revoke-and-remint is rotation.
"""

import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.knowledge_base.bundles import build_kb_bundle, canonical_bundle_hash
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.chunk import Chunk
from app.models.federation import FederationFeed, FederationSubscription
from app.models.knowledge_base import KnowledgeBase
from app.models.source import Source
from app.models.user import User

FEED_FETCH_TIMEOUT_S = 30
FEED_MAX_BYTES = 200 * 1024 * 1024


def check_feed_url(url: str) -> str | None:
    """Pure guard for subscription targets (OQ-96): http/https only, sane
    shape. Returns an error string or None."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except ValueError:
        return "feed_url is not a valid URL"
    if parsed.scheme not in ("http", "https"):
        return "feed_url must be http(s)"
    if not parsed.hostname:
        return "feed_url has no host"
    return None


def should_sync(local_hash: str, remote_meta: dict) -> bool:
    """Pure sync decision (OQ-97): only when the remote's canonical bundle
    hash differs. Missing/garbage remote hash counts as changed — the full
    fetch will then validate properly."""
    remote_hash = remote_meta.get("bundle_hash")
    return not (isinstance(remote_hash, str) and remote_hash == local_hash)


class FederationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Feeds (OQ-95) ─────────────────────────────────────────────────────────

    async def _owned_kb(self, kb_id: str, user: User) -> KnowledgeBase:
        kb = await KnowledgeBaseService(self.db).get_by_id(kb_id, user)  # owner-only
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
        return kb

    async def enable_feed(self, kb_id: str, user: User) -> FederationFeed:
        """Mint (or return the existing) feed for an owned KB. Enabling a
        feed is a stronger act than export (OQ-77) — owner only."""
        kb = await self._owned_kb(kb_id, user)
        existing = (
            await self.db.execute(select(FederationFeed).where(FederationFeed.kb_id == kb.id))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        feed = FederationFeed(kb_id=kb.id, slug=secrets.token_urlsafe(32))
        self.db.add(feed)
        await self.db.commit()
        await self.db.refresh(feed)
        return feed

    async def get_feed(self, kb_id: str, user: User) -> FederationFeed | None:
        await self._owned_kb(kb_id, user)
        return (
            await self.db.execute(select(FederationFeed).where(FederationFeed.kb_id == kb_id))
        ).scalar_one_or_none()

    async def revoke_feed(self, kb_id: str, user: User) -> None:
        await self._owned_kb(kb_id, user)
        feed = (
            await self.db.execute(select(FederationFeed).where(FederationFeed.kb_id == kb_id))
        ).scalar_one_or_none()
        if feed is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No feed for this knowledge base")
        await self.db.delete(feed)
        await self.db.commit()

    async def _bundle_for_slug(self, slug: str) -> tuple[KnowledgeBase, dict]:
        """Resolve a capability slug to its KB's bundle — 404 non-leak for
        unknown/revoked slugs (indistinguishable by design)."""
        feed = (
            await self.db.execute(select(FederationFeed).where(FederationFeed.slug == slug))
        ).scalar_one_or_none()
        if feed is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feed not found")
        kb = await self.db.get(KnowledgeBase, feed.kb_id)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feed not found")
        sources = list(
            (await self.db.execute(
                select(Source).where(Source.kb_id == kb.id).order_by(Source.created_at, Source.id)
            )).scalars().all()
        )
        chunks = list(
            (await self.db.execute(
                select(Chunk)
                .where(Chunk.vector_namespace == kb.vector_namespace)
                .order_by(Chunk.source_id, Chunk.seq)
            )).scalars().all()
        )
        return kb, build_kb_bundle(kb.title, sources, chunks)

    async def serve_bundle(self, slug: str) -> dict:
        _, bundle = await self._bundle_for_slug(slug)
        return bundle

    async def serve_meta(self, slug: str) -> dict:
        kb, bundle = await self._bundle_for_slug(slug)
        return {
            "title": kb.title,
            "source_count": len(bundle["sources"]),
            "chunk_count": len(bundle["chunks"]),
            "bundle_hash": canonical_bundle_hash(bundle),
        }

    # ── Subscriptions (OQ-96/97) ──────────────────────────────────────────────

    @staticmethod
    async def _fetch_json(url: str) -> dict:
        """Capped remote fetch — remote bundles are attacker-controlled twice
        over (OQ-96): scheme-checked URL, timeout, size cap, no redirects."""
        import httpx

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(FEED_FETCH_TIMEOUT_S),
            ) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise HTTPException(
                            status.HTTP_502_BAD_GATEWAY,
                            detail=f"Feed responded {resp.status_code}",
                        )
                    body = b""
                    async for chunk in resp.aiter_bytes():
                        body += chunk
                        if len(body) > FEED_MAX_BYTES:
                            raise HTTPException(
                                status.HTTP_502_BAD_GATEWAY, detail="Feed exceeds 200MB"
                            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail=f"Feed unreachable: {exc.__class__.__name__}"
            )
        import json

        try:
            return json.loads(body)
        except ValueError:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Feed did not return JSON")

    async def _fetch_and_validate_bundle(self, feed_url: str) -> tuple[dict, str]:
        from app.domains.knowledge_base.bundles import validate_bundle

        bundle = await self._fetch_json(feed_url)
        error = validate_bundle(bundle)
        if error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Remote bundle invalid: {error}"
            )
        return bundle, canonical_bundle_hash(bundle)

    async def _enqueue_reembed(self, kb_id: str, namespace: str) -> None:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.xadd("import.jobs", {"kb_id": kb_id, "vector_namespace": namespace})

    async def subscribe(self, feed_url: str, user: User) -> FederationSubscription:
        """Create a private mirror KB from a remote feed (OQ-96)."""
        from app.domains.knowledge_base.bundle_io import materialize_plan
        from app.domains.knowledge_base.bundles import plan_import

        error = check_feed_url(feed_url)
        if error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

        bundle, bundle_hash = await self._fetch_and_validate_bundle(feed_url)

        kb = await KnowledgeBaseService(self.db).create(
            user, title=str(bundle["kb"]["title"]).strip()[:200]
        )
        plan = plan_import(bundle, kb.embedding_model_id)
        needs_embedding = materialize_plan(self.db, user.id, kb, plan)

        sub = FederationSubscription(
            kb_id=kb.id,
            owner_user_id=user.id,
            feed_url=feed_url,
            bundle_hash=bundle_hash,
            last_synced_at=datetime.now(timezone.utc),
        )
        self.db.add(sub)

        # Commit BEFORE enqueue (OQ-73); capture scalars first
        kb_id_val, namespace = kb.id, kb.vector_namespace
        await self.db.commit()
        if needs_embedding:
            await self._enqueue_reembed(kb_id_val, namespace)
        await self.db.refresh(sub)
        return sub

    async def _owned_subscription(self, sub_id: str, user: User) -> FederationSubscription:
        sub = await self.db.get(FederationSubscription, sub_id)
        if sub is None or sub.owner_user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        return sub

    async def get_for_kb(self, kb_id: str, user: User) -> FederationSubscription | None:
        """The mirror record for a KB the user can read (null for non-mirrors)."""
        kb = await KnowledgeBaseService(self.db).get_readable_by_id(kb_id, user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
        return (
            await self.db.execute(
                select(FederationSubscription).where(FederationSubscription.kb_id == kb_id)
            )
        ).scalar_one_or_none()

    async def sync(self, sub_id: str, user: User) -> dict:
        """Meta-first re-sync (OQ-97): unchanged hash costs one request;
        changed → full replace into the SAME kb (links/grants/paths survive)."""
        from app.domains.knowledge_base.bundle_io import materialize_plan, wipe_kb_sources
        from app.domains.knowledge_base.bundles import plan_import

        sub = await self._owned_subscription(sub_id, user)
        meta = await self._fetch_json(sub.feed_url.rstrip("/") + "/meta")
        if not should_sync(sub.bundle_hash, meta):
            sub.last_synced_at = datetime.now(timezone.utc)
            await self.db.commit()
            return {"changed": False}

        bundle, bundle_hash = await self._fetch_and_validate_bundle(sub.feed_url)
        kb = await self.db.get(KnowledgeBase, sub.kb_id)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mirror knowledge base missing")

        await wipe_kb_sources(self.db, kb)
        plan = plan_import(bundle, kb.embedding_model_id)
        needs_embedding = materialize_plan(self.db, user.id, kb, plan)
        sub.bundle_hash = bundle_hash
        sub.last_synced_at = datetime.now(timezone.utc)

        kb_id_val, namespace = kb.id, kb.vector_namespace
        n_sources, n_chunks = len(plan["sources"]), len(plan["chunks"])
        await self.db.commit()
        if needs_embedding:
            await self._enqueue_reembed(kb_id_val, namespace)
        return {
            "changed": True,
            "source_count": n_sources,
            "chunk_count": n_chunks,
            "reindexing": needs_embedding,
        }

    async def unsubscribe(self, sub_id: str, user: User) -> None:
        """Delete the subscription record — the KB stays and becomes an
        ordinary local KB (OQ-98's escape hatch)."""
        sub = await self._owned_subscription(sub_id, user)
        await self.db.delete(sub)
        await self.db.commit()
