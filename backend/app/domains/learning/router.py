from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.learning.discussions import DiscussionService
from app.domains.learning.service import LearningService
from app.models.user import User
from app.schemas.learning import (
    AttemptRequest,
    AttemptResult,
    ConceptNoteOut,
    CreateLearningPathRequest,
    CreatePostRequest,
    CreateThreadRequest,
    LearningPathOut,
    LearningPathSummary,
    PathAnalyticsOut,
    PathConceptOut,
    PostOut,
    ThreadOut,
    ThreadSummaryOut,
    UpdateConceptRequest,
    UpdatePathRequest,
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
    from app.domains.knowledge_base.service import KnowledgeBaseService

    kb = await KnowledgeBaseService(db).get_readable_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

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
                # Non-pruned only — one truthful denominator with completion_pct (OQ-43)
                concept_count=len(active),
                learned_count=learned_count,
                completion_pct=round(learned_count / len(active), 4) if active else 0.0,
                created_at=p.created_at,
                owner=p.owner,
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
    path = await svc.get_readable_path(path_id, user)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    out = LearningPathOut.model_validate(path)
    out.learned_concept_ids = sorted(
        await svc.learned_concept_ids(user, [c.id for c in path.concepts])
    )
    _shape_assessment_items(out, is_owner=path.user_id == user.id, user_id=user.id)
    _apply_gates(out, await svc.gate_states(path, user))
    return out


def _apply_gates(out: LearningPathOut, gates: dict[str, dict] | None) -> None:
    """Stamp per-concept gate state and redact locked concepts in hard mode
    (docs/14, OQ-48/49). No-op when gates is None (mode off, or owner)."""
    from app.schemas.learning import ConceptGateOut

    if gates is None:
        return
    hard = out.mastery_mode == "hard"
    for concept in out.concepts:
        state = gates.get(concept.id)
        if state is None:  # pruned concepts neither gate nor lock
            continue
        concept.locked = state["locked"]
        concept.gate = ConceptGateOut(
            mastered=state["mastered"],
            correct_items=state["correct_items"],
            item_count=state["item_count"],
        )
        if hard and concept.locked:
            # Redaction is what makes hard mode honest — a 422 on writes
            # alone would still hand the content to anyone with curl
            concept.explanation_text = ""
            concept.explanation_passage_ids = []
            concept.source_passages = []
            concept.assessment_items = []
            concept.instructor_annotation = None


def _shape_assessment_items(out: LearningPathOut, *, is_owner: bool, user_id: str) -> None:
    """Build MC choices and strip answer keys from learner responses (KC-055).

    Choices = correct answer + distractors, shuffled deterministically per
    (item, user) so a refresh keeps the order; ids are post-shuffle indexes so
    nothing in the payload identifies the correct option. Grading stays
    server-side and text-based, so choice clicks submit the choice text.
    """
    import hashlib
    import random

    from app.schemas.learning import ChoiceOut

    for concept in out.concepts:
        for item in concept.assessment_items:
            if item.correct_answer and item.distractors:
                texts = [item.correct_answer] + [d.text for d in item.distractors]
                seed = int(hashlib.md5(f"{item.id}:{user_id}".encode()).hexdigest(), 16)
                random.Random(seed).shuffle(texts)
                item.choices = [ChoiceOut(id=f"c{i}", text=t) for i, t in enumerate(texts)]
            if not is_owner:
                # Learners must not receive the answer key or the distractor
                # list (either identifies the correct choice by elimination).
                item.correct_answer = None
                item.distractors = []


@router.get(
    "/learning-paths/{path_id}/analytics",
    response_model=PathAnalyticsOut,
    summary="Owner-only cohort analytics: per-learner progress and per-concept attempt stats",
)
async def get_path_analytics(
    path_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PathAnalyticsOut:
    svc = LearningService(db)
    result = await svc.path_analytics(path_id, user)
    return PathAnalyticsOut(**result)


@router.patch(
    "/learning-paths/{path_id}",
    response_model=LearningPathOut,
    summary="Instructor: update path settings (mastery gating)",
)
async def update_learning_path(
    path_id: str,
    req: UpdatePathRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LearningPathOut:
    svc = LearningService(db)
    path = await svc.update_path(
        path_id,
        user,
        mastery_mode=req.mastery_mode,
        mastery_threshold=req.mastery_threshold,
    )
    out = LearningPathOut.model_validate(path)
    out.learned_concept_ids = sorted(
        await svc.learned_concept_ids(user, [c.id for c in path.concepts])
    )
    _shape_assessment_items(out, is_owner=True, user_id=user.id)
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


# ── Discussion threads (docs/13, KC-083) ─────────────────────────────────────


def _thread_summary(thread, post_count: int) -> ThreadSummaryOut:
    return ThreadSummaryOut(
        id=thread.id,
        concept_id=thread.concept_id,
        title=thread.title,
        body=thread.body,
        passage_chunk_id=thread.passage_chunk_id,
        passage_excerpt=thread.passage_excerpt,
        author=thread.author,
        post_count=post_count,
        created_at=thread.created_at,
    )


@router.get(
    "/learning-paths/{path_id}/concepts/{concept_id}/threads",
    response_model=list[ThreadSummaryOut],
    summary="List discussion threads on a concept (newest first)",
)
async def list_threads(
    path_id: str,
    concept_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ThreadSummaryOut]:
    svc = DiscussionService(db)
    rows = await svc.list_threads(path_id, concept_id, user, limit=limit, offset=offset)
    return [_thread_summary(t, n) for t, n in rows]


@router.post(
    "/learning-paths/{path_id}/concepts/{concept_id}/threads",
    response_model=ThreadOut,
    status_code=201,
    summary="Open a discussion thread on a concept (optionally anchored to one of its passages)",
)
async def create_thread(
    path_id: str,
    concept_id: str,
    req: CreateThreadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ThreadOut:
    svc = DiscussionService(db)
    thread = await svc.create_thread(
        path_id, concept_id, user, req.title, req.body, req.passage_chunk_id
    )
    return ThreadOut(**_thread_summary(thread, 0).model_dump(), posts=[])


@router.get(
    "/learning-paths/{path_id}/threads/{thread_id}",
    response_model=ThreadOut,
    summary="Get a thread with its posts (oldest first)",
)
async def get_thread(
    path_id: str,
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ThreadOut:
    svc = DiscussionService(db)
    thread = await svc.get_thread(path_id, thread_id, user)
    out = ThreadOut(**_thread_summary(thread, len(thread.posts)).model_dump())
    out.posts = [PostOut.model_validate(p) for p in thread.posts]
    return out


@router.post(
    "/learning-paths/{path_id}/threads/{thread_id}/posts",
    response_model=PostOut,
    status_code=201,
    summary="Reply to a discussion thread",
)
async def create_post(
    path_id: str,
    thread_id: str,
    req: CreatePostRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostOut:
    svc = DiscussionService(db)
    post = await svc.create_post(path_id, thread_id, user, req.body)
    return PostOut.model_validate(post)


@router.delete(
    "/learning-paths/{path_id}/threads/{thread_id}/posts/{post_id}",
    status_code=204,
    summary="Delete a post (author or path owner)",
)
async def delete_post(
    path_id: str,
    thread_id: str,
    post_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    svc = DiscussionService(db)
    await svc.delete_post(path_id, thread_id, post_id, user)
