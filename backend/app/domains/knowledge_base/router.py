from pydantic import BaseModel
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseOut

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
