from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.source import Source
from app.models.user import User
from app.schemas.knowledge_base import ChunkSearchResult, KnowledgeBaseOut
from app.schemas.source import SourceStatusOut

router = APIRouter(prefix="/kbs", tags=["knowledge-bases"])


class CreateKBRequest(BaseModel):
    title: str


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_kbs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[KnowledgeBaseOut]:
    svc = KnowledgeBaseService(db)
    kbs = await svc.list_for_user(user)
    return [KnowledgeBaseOut.model_validate(kb) for kb in kbs]


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_kb(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return KnowledgeBaseOut.model_validate(kb)


@router.get("/{kb_id}/sources", response_model=list[SourceStatusOut])
async def list_kb_sources(
    kb_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SourceStatusOut]:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    result = await db.execute(
        select(Source)
        .where(Source.kb_id == kb_id, Source.owner_user_id == user.id)
        .order_by(Source.created_at.desc())
        .limit(limit)
    )
    return [SourceStatusOut.model_validate(s) for s in result.scalars().all()]


@router.get(
    "/{kb_id}/search",
    response_model=list[ChunkSearchResult],
    summary="Semantic search within a KB's sources (namespace-scoped pgvector)",
)
async def search_kb(
    kb_id: str,
    q: str = Query(min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChunkSearchResult]:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    from app.domains.generation.ollama import embed
    from app.domains.retrieval.service import RetrievalService

    query_vec = (await embed([q]))[0]
    chunks = await RetrievalService(db).retrieve(query_vec, kb.vector_namespace, top_k=limit)

    source_ids = {c.source_id for c in chunks}
    sources = {}
    if source_ids:
        result = await db.execute(select(Source).where(Source.id.in_(source_ids)))
        sources = {s.id: s for s in result.scalars().all()}

    return [
        ChunkSearchResult(
            chunk_id=c.chunk_id,
            source_id=c.source_id,
            source_title=sources[c.source_id].title if c.source_id in sources else "(unknown source)",
            source_type=sources[c.source_id].type if c.source_id in sources else "unknown",
            locator=c.locator,
            text=c.text,
            score=c.score,
        )
        for c in chunks
    ]


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_kb(
    req: CreateKBRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    svc = KnowledgeBaseService(db)
    kb = await svc.create(user, req.title)
    await db.commit()
    await db.refresh(kb)
    return KnowledgeBaseOut.model_validate(kb)
