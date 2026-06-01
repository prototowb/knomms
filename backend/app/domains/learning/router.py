from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.learning.service import LearningService
from app.models.user import User
from app.schemas.learning import (
    AttemptRequest,
    AttemptResult,
    CreateLearningPathRequest,
    LearningPathOut,
    LearningPathSummary,
    PathConceptOut,
    UpdateConceptRequest,
)

router = APIRouter(tags=["learning"])


@router.post(
    "/kbs/{kb_id}/learning-paths",
    response_model=LearningPathOut,
    status_code=201,
    summary="Generate a learning path from this KB's corpus",
)
async def create_learning_path(
    kb_id: str,
    req: CreateLearningPathRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathOut:
    svc = LearningService(db)
    path = await svc.create_draft(kb_id, user, req.learning_goal, req.time_budget_hours)
    full = await svc.get_path(path.id, user)
    if full is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Path not found after creation")
    return LearningPathOut.model_validate(full)


@router.get(
    "/kbs/{kb_id}/learning-paths",
    response_model=list[LearningPathSummary],
    summary="List learning paths for a KB",
)
async def list_learning_paths(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LearningPathSummary]:
    svc = LearningService(db)
    paths = await svc.list_paths(kb_id, user)
    result = []
    for p in paths:
        # concepts may not be loaded — load count separately if needed
        concept_count = len(p.concepts) if hasattr(p, "concepts") and p.concepts else 0
        result.append(
            LearningPathSummary(
                id=p.id,
                kb_id=p.kb_id,
                learning_goal=p.learning_goal,
                status=p.status,
                version=p.version,
                concept_count=concept_count,
                created_at=p.created_at,
            )
        )
    return result


@router.get(
    "/learning-paths/{path_id}",
    response_model=LearningPathOut,
    summary="Get a learning path with all concepts and assessments",
)
async def get_learning_path(
    path_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathOut:
    svc = LearningService(db)
    path = await svc.get_path(path_id, user)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return LearningPathOut.model_validate(path)


@router.patch(
    "/learning-paths/{path_id}/concepts/{concept_id}",
    response_model=PathConceptOut,
    summary="Instructor: accept, prune, or annotate a concept",
)
async def update_concept(
    path_id: str,
    concept_id: str,
    req: UpdateConceptRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PathConceptOut:
    svc = LearningService(db)
    concept = await svc.update_concept(
        path_id,
        concept_id,
        user,
        concept_status=req.status,
        instructor_annotation=req.instructor_annotation,
    )
    return PathConceptOut.model_validate(concept)


@router.post(
    "/learning-paths/{path_id}/publish",
    response_model=LearningPathOut,
    summary="Publish a draft learning path",
)
async def publish_learning_path(
    path_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathOut:
    svc = LearningService(db)
    path = await svc.publish_path(path_id, user)
    full = await svc.get_path(path.id, user)
    if full is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Path not found after publish")
    return LearningPathOut.model_validate(full)


@router.post(
    "/learning-paths/{path_id}/concepts/{concept_id}/items/{item_id}/attempt",
    response_model=AttemptResult,
    summary="Submit an MC answer and receive grounded feedback",
)
async def attempt_assessment(
    path_id: str,
    concept_id: str,
    item_id: str,
    req: AttemptRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptResult:
    svc = LearningService(db)
    result = await svc.grade_attempt(path_id, concept_id, item_id, user, req.answer)
    return AttemptResult(**result)
