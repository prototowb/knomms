from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.source import Source
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseOut
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
