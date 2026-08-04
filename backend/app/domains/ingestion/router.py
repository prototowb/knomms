from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.ingestion.service import IngestionService
from app.models.user import User
from app.schemas.source import SourceOut, SourceStatusOut, SourceSubmit

router = APIRouter(prefix="/sources", tags=["ingestion"])


@router.post("/", response_model=SourceOut, status_code=status.HTTP_202_ACCEPTED)
async def submit_url(
    body: SourceSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceOut:
    """Submit a URL for ingestion. Returns immediately; ingestion is async."""
    svc = IngestionService(db)
    source, kb_id = await svc.submit_url(body, current_user)
    out = SourceOut.model_validate(source)
    out.kb_id = kb_id
    return out


@router.post("/upload", response_model=SourceOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    kb_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceOut:
    """Upload a file (PDF, DOCX, TXT) for ingestion."""
    svc = IngestionService(db)
    source, resolved_kb_id = await svc.submit_file(file, kb_id, current_user)
    out = SourceOut.model_validate(source)
    out.kb_id = resolved_kb_id
    return out


@router.get("/{source_id}", response_model=SourceStatusOut)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceStatusOut:
    svc = IngestionService(db)
    source = await svc.get_source(source_id, current_user)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    if source.owner_user_id != current_user.id:
        # Readers of a shared KB may poll ingestion status of its sources
        from app.domains.knowledge_base.service import KnowledgeBaseService

        kb = None
        if source.kb_id:
            kb = await KnowledgeBaseService(db).get_readable_by_id(source.kb_id, current_user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    return SourceStatusOut.model_validate(source)


@router.websocket("/{source_id}/progress")
async def source_progress(
    websocket: WebSocket,
    source_id: str,
) -> None:
    """WebSocket: streams ingestion progress events for a source.

    Client subscribes to Redis pub/sub channel source:{source_id}:progress.
    Events: {"status": "processing|chunked|embedded|failed", "progress_pct": 0-100}
    """
    await websocket.accept()
    redis = await get_redis()
    channel = f"source:{source_id}:progress"

    async with redis.pubsub() as pubsub:
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
                    if '"status": "embedded"' in message["data"] or '"status": "failed"' in message["data"]:
                        break
        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe(channel)
