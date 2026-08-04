from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.learning.service import LearningService
from app.models.user import User
from app.schemas.learning import (
    AttemptRequest,
    AttemptResult,
    ConceptNoteOut,
    CreateLearningPathRequest,
    LearningPathOut,
    LearningPathSummary,
    PathConceptOut,
    UpdateConceptRequest,
    UpsertNoteRequest,
)

router = APIRouter(tags=["learning"])

CURRICULUM_STREAM_KEY = "curriculum.jobs"


@router.post(
    "/kbs/{kb_id}/learning-paths",
    response_model=LearningPathOut,
    status_code=202,
    summary="Enqueue a learning path generation job from this KB's corpus",
)
async def create_learning_path(
    kb_id: str,
    req: CreateLearningPathRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathOut:
    svc = LearningService(db)
    path, vector_namespace = await svc.create_stub(kb_id, user, req.learning_goal, req.time_budget_hours)
    redis = await get_redis()
    await redis.xadd(
        CURRICULUM_STREAM_KEY,
        {
            "path_id": path.id,
            "kb_id": kb_id,
            "vector_namespace": vector_namespace,
        },
    )
    return LearningPathOut(
        id=path.id,
        kb_id=path.kb_id,
        learning_goal=path.learning_goal,
        status=path.status,
        version=path.version,
        time_budget_hours=path.time_budget_hours,
        created_at=path.created_at,
        updated_at=path.updated_at,
        concepts=[],
    )


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
    all_concept_ids = [c.id for p in paths for c in (p.concepts or [])]
    learned = await svc.learned_concept_ids(user, all_concept_ids)
    result = []
    for p in paths:
        # Learner-facing completion counts non-pruned concepts only
        active = [c for c in (p.concepts or []) if c.status != "pruned"]
        learned_count = sum(1 for c in active if c.id in learned)
        result.append(
            LearningPathSummary(
                id=p.id,
                kb_id=p.kb_id,
                learning_goal=p.learning_goal,
                status=p.status,
                version=p.version,
                concept_count=len(p.concepts or []),
                learned_count=learned_count,
                completion_pct=round(learned_count / len(active), 4) if active else 0.0,
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
    out = LearningPathOut.model_validate(path)
    out.learned_concept_ids = sorted(
        await svc.learned_concept_ids(user, [c.id for c in path.concepts])
    )
    return out


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
    "/learning-paths/{path_id}/concepts/{concept_id}/learned",
    summary="Mark a concept as learned for the current user (idempotent)",
)
async def mark_learned(
    path_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = LearningService(db)
    await svc.set_learned(path_id, concept_id, user, learned=True)
    return {"learned": True}


@router.delete(
    "/learning-paths/{path_id}/concepts/{concept_id}/learned",
    summary="Unmark a concept as learned for the current user (idempotent)",
)
async def unmark_learned(
    path_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = LearningService(db)
    await svc.set_learned(path_id, concept_id, user, learned=False)
    return {"learned": False}


@router.get(
    "/learning-paths/{path_id}/concepts/{concept_id}/note",
    response_model=ConceptNoteOut | None,
    summary="Get the current user's private note on a concept (null if none)",
)
async def get_concept_note(
    path_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConceptNoteOut | None:
    svc = LearningService(db)
    note = await svc.get_note(path_id, concept_id, user)
    return ConceptNoteOut.model_validate(note) if note else None


@router.put(
    "/learning-paths/{path_id}/concepts/{concept_id}/note",
    response_model=ConceptNoteOut,
    summary="Create or replace the current user's private note on a concept",
)
async def upsert_concept_note(
    path_id: str,
    concept_id: str,
    req: UpsertNoteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConceptNoteOut:
    svc = LearningService(db)
    note = await svc.upsert_note(path_id, concept_id, user, req.body)
    return ConceptNoteOut.model_validate(note)


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
