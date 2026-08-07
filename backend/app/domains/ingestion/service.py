"""Ingestion service — accepts a source, dispatches to Redis Streams worker."""

import json
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.source import Source
from app.models.user import User
from app.schemas.source import SourceSubmit

# Redis Stream key — matches the worker consumer
STREAM_KEY = "ingestion.jobs"


class IngestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_url(self, data: SourceSubmit, user: User) -> tuple[Source, str]:
        """Submit a URL for ingestion. Returns (source, kb_id)."""
        if not data.url:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="url is required")

        kb = await self._resolve_kb(data.kb_id, user)
        url_str = str(data.url)

        # YouTube URLs become video sources (docs/15, OQ-55) — the worker
        # dispatches extractors on the type, so it must be right at creation
        from app.domains.ingestion.extractors.video import parse_video_url

        video_id = parse_video_url(url_str)
        if video_id:
            source_type = "video"
            title = await _video_title(url_str, video_id)
        else:
            source_type = "web_page"
            title = _title_from_url(url_str)

        source = Source(
            id=str(uuid.uuid4()),
            owner_user_id=user.id,
            type=source_type,
            raw_url=url_str,
            title=title,
            kb_id=kb.id,
            ingestion_status="pending",
        )
        self.db.add(source)
        # Commit BEFORE enqueue — the worker must never see a job for an
        # uncommitted Source row, or the source is stuck 'pending' forever
        # (the KC-077 lesson; race caught live in KC-095)
        kb_id_val, namespace = kb.id, kb.vector_namespace
        await self.db.commit()
        await self.db.refresh(source)

        await self._dispatch(source.id, user.id, kb_id_val, namespace)
        return source, kb_id_val

    async def submit_file(self, file: UploadFile, kb_id: str | None, user: User) -> tuple[Source, str]:
        """Submit an uploaded file for ingestion. Returns (source, kb_id)."""
        if not file.filename:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="filename is required")

        suffix = file.filename.rsplit(".", 1)[-1].lower()
        source_type = _type_from_suffix(suffix)

        kb = await self._resolve_kb(kb_id, user)

        content = await file.read()
        if len(content) > 200 * 1024 * 1024:  # 200MB limit
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 200MB limit")

        source_id = str(uuid.uuid4())
        # Storage key: raw/{user_id}/{source_id}/{filename}
        storage_key = f"raw/{user.id}/{source_id}/{file.filename}"

        source = Source(
            id=source_id,
            owner_user_id=user.id,
            type=source_type,
            storage_key=storage_key,
            title=file.filename,
            kb_id=kb.id,
            ingestion_status="pending",
        )
        self.db.add(source)
        await self.db.flush()

        # Write to MinIO for durable storage (the pipeline's MinIO fallback path
        # requires the object to actually exist there).
        from app.core.config import settings as _settings
        from app.core.storage import write_object
        await write_object(_settings.minio_bucket, storage_key, content)

        # Also cache in Redis for fast worker pickup (TTL 1 hour avoids a MinIO
        # round-trip for files processed quickly).
        redis = await get_redis()
        await redis.setex(f"upload:{source_id}", 3600, content)

        # Commit BEFORE enqueue (same race as submit_url — KC-095)
        kb_id_val, namespace = kb.id, kb.vector_namespace
        await self.db.commit()
        await self.db.refresh(source)

        await self._dispatch(source.id, user.id, kb_id_val, namespace, upload=True)
        return source, kb_id_val

    async def get_source(self, source_id: str, user: User) -> Source | None:
        return await self.db.get(Source, source_id)

    async def _resolve_kb(self, kb_id: str | None, user: User):
        kb_svc = KnowledgeBaseService(self.db)
        if kb_id:
            # Adding sources is the KB's OQ-18 editor surface — owner or editor
            # grant (docs/10-teams-and-acls.md)
            kb = await kb_svc.get_editable_by_id(kb_id, user)
            if kb is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
            return kb
        return await kb_svc.get_or_create_default(user)

    async def _dispatch(
        self,
        source_id: str,
        user_id: str,
        kb_id: str,
        vector_namespace: str,
        upload: bool = False,
    ) -> None:
        redis = await get_redis()
        # Redis Streams job-message contract (matched by worker/pipeline.py)
        await redis.xadd(
            STREAM_KEY,
            {
                "source_id": source_id,
                "user_id": user_id,
                "kb_id": kb_id,
                "vector_namespace": vector_namespace,
                "upload": "1" if upload else "0",
            },
        )


async def _video_title(url: str, video_id: str) -> str:
    """Best-effort oEmbed title (docs/15, OQ-60) — never blocks submission."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
            )
            resp.raise_for_status()
            title = (resp.json().get("title") or "").strip()
            if title:
                return title[:200]
    except Exception:
        pass
    return f"youtube:{video_id}"


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return path.rsplit("/", 1)[-1] or parsed.netloc or url[:100]


def _type_from_suffix(suffix: str) -> str:
    mapping = {
        "pdf": "pdf",
        "docx": "plain_text",
        "doc": "plain_text",
        "txt": "plain_text",
        "md": "plain_text",
        "epub": "epub",
    }
    return mapping.get(suffix, "plain_text")
