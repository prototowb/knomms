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
