"""Learning service — DB operations for learning paths."""

import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.chunk import Chunk
from app.models.knowledge_base import KnowledgeBase
from app.models.learning import (
    AssessmentAttempt,
    AssessmentItem,
    ConceptNote,
    ConceptProgress,
    LearningPath,
    PathConcept,
)
from app.models.user import User


def _normalize_answer(text: str) -> str:
    """Canonical form for answer comparison: NFC unicode, lowercase, collapsed whitespace, no edge punctuation."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    return text


def _match_distractor(norm_answer: str, distractors) -> tuple[str | None, str | None]:
    """Match a normalised wrong answer against an item's distractors.

    Returns (distractor_id, misconception_label) for the first normalised
    match, else (None, None). Pure — distractors only need .id/.text/
    .misconception_label attributes.
    """
    for d in distractors:
        if norm_answer == _normalize_answer(d.text):
            return d.id, d.misconception_label
    return None, None


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_stub(
        self,
        kb_id: str,
        user: User,
        learning_goal: str,
        time_budget_hours: float | None,
    ) -> tuple[LearningPath, str]:
        """Authz + fail-fast chunks check, then create a LearningPath(status='generating').

        Returns (path, vector_namespace) — the namespace is needed by the caller to enqueue the job.
        Raises 404/422 synchronously so the client gets immediate feedback on bad inputs.
        """
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_by_id(kb_id, user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        # Fail fast: ensure there are embedded chunks before accepting the job
        has_chunks = await self.db.scalar(
            select(Chunk.id)
            .where(
                Chunk.vector_namespace == kb.vector_namespace,
                Chunk.embedding.is_not(None),
            )
            .limit(1)
        )
        if not has_chunks:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Knowledge base has no indexed chunks — ingest a source first",
            )

        path = LearningPath(
            kb_id=kb_id,
            user_id=user.id,
            learning_goal=learning_goal,
            time_budget_hours=time_budget_hours,
            status="generating",
        )
        self.db.add(path)
        await self.db.commit()
        await self.db.refresh(path)
        return path, kb.vector_namespace

    _PATH_LOAD_OPTIONS = (
        selectinload(LearningPath.concepts)
        .selectinload(PathConcept.assessment_items)
        .selectinload(AssessmentItem.distractors),
        selectinload(LearningPath.owner),
    )

    async def get_path(self, path_id: str, user: User) -> LearningPath | None:
        """Owner-only lookup — the guard for instructor actions (update/publish)."""
        stmt = (
            select(LearningPath)
            .where(LearningPath.id == path_id, LearningPath.user_id == user.id)
            .options(*self._PATH_LOAD_OPTIONS)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _readable_kb_exists(user: User):
        """Correlated EXISTS: the path's KB is readable by this user
        (docs/09 OQ-7 — team = same org; docs/10 OQ-17 — KB grants flow to paths)."""
        from app.domains.organisations.predicates import readable_clause

        return (
            select(KnowledgeBase.id)
            .where(
                KnowledgeBase.id == LearningPath.kb_id,
                or_(
                    KnowledgeBase.owner_user_id == user.id,
                    readable_clause(KnowledgeBase, "kb", user),
                ),
            )
            .exists()
        )

    async def get_readable_path(self, path_id: str, user: User) -> LearningPath | None:
        """Learner lookup: the owner, or anyone when the path is published and
        its KB is team/public-readable."""
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.id == path_id,
                or_(
                    LearningPath.user_id == user.id,
                    and_(
                        LearningPath.status == "published",
                        self._readable_kb_exists(user),
                    ),
                ),
            )
            .options(*self._PATH_LOAD_OPTIONS)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paths(self, kb_id: str, user: User) -> list[LearningPath]:
        """Own paths plus published paths on this KB (KB readability is checked
        at the router — this only decides which rows a reader may see)."""
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.kb_id == kb_id,
                or_(
                    LearningPath.user_id == user.id,
                    LearningPath.status == "published",
                ),
            )
            .options(selectinload(LearningPath.concepts), selectinload(LearningPath.owner))
            .order_by(LearningPath.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_readable_concept_id(self, path_id: str, concept_id: str, user: User) -> str:
        """Authz helper for learner actions (attempt/note/learned): 404 unless
        the concept belongs to a path the user can read."""
        path = await self.get_readable_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        if not any(c.id == concept_id for c in path.concepts):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Concept not found")
        return concept_id

    async def set_learned(self, path_id: str, concept_id: str, user: User, learned: bool) -> bool:
        """Idempotently mark/unmark a concept as learned for this user."""
        await self._get_readable_concept_id(path_id, concept_id, user)
        stmt = select(ConceptProgress).where(
            ConceptProgress.user_id == user.id, ConceptProgress.concept_id == concept_id
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if learned and existing is None:
            self.db.add(ConceptProgress(user_id=user.id, concept_id=concept_id))
            await self.db.commit()
        elif not learned and existing is not None:
            await self.db.delete(existing)
            await self.db.commit()
        return learned

    async def learned_concept_ids(self, user: User, concept_ids: list[str]) -> set[str]:
        """Which of the given concepts has this user marked as learned."""
        if not concept_ids:
            return set()
        stmt = select(ConceptProgress.concept_id).where(
            ConceptProgress.user_id == user.id,
            ConceptProgress.concept_id.in_(concept_ids),
        )
        return set((await self.db.execute(stmt)).scalars().all())

    async def get_note(self, path_id: str, concept_id: str, user: User) -> ConceptNote | None:
        await self._get_readable_concept_id(path_id, concept_id, user)
        stmt = select(ConceptNote).where(
            ConceptNote.user_id == user.id, ConceptNote.concept_id == concept_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def upsert_note(self, path_id: str, concept_id: str, user: User, body: str) -> ConceptNote:
        note = await self.get_note(path_id, concept_id, user)
        if note is None:
            note = ConceptNote(user_id=user.id, concept_id=concept_id, body=body)
            self.db.add(note)
        else:
            note.body = body
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def update_concept(
        self,
        path_id: str,
        concept_id: str,
        user: User,
        *,
        concept_status: str | None = None,
        instructor_annotation: str | None = None,
    ) -> PathConcept:
        path = await self.get_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        stmt = select(PathConcept).where(
            PathConcept.id == concept_id, PathConcept.path_id == path_id
        )
        concept = (await self.db.execute(stmt)).scalar_one_or_none()
        if concept is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Concept not found")

        if concept_status is not None:
            if concept_status not in ("pending", "accepted", "pruned"):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status value"
                )
            concept.status = concept_status
        if instructor_annotation is not None:
            concept.instructor_annotation = instructor_annotation

        await self.db.commit()
        await self.db.refresh(concept)
        return concept

    async def publish_path(self, path_id: str, user: User) -> LearningPath:
        path = await self.get_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        path.status = "published"
        await self.db.commit()
        await self.db.refresh(path)
        return path

    async def path_analytics(self, path_id: str, user: User) -> dict:
        """Owner-only cohort analytics (docs/13, OQ-39) — 404 for everyone else
        so a path's learner roster never leaks through published paths."""
        from app.domains.learning.analytics import build_analytics
        from app.models.learning import AssessmentAttempt, Distractor

        path = await self.get_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        active = [c for c in path.concepts if c.status != "pruned"]
        active_ids = [c.id for c in active]

        progress_rows: list[dict] = []
        if active_ids:
            rows = (
                await self.db.execute(
                    select(ConceptProgress.user_id, ConceptProgress.concept_id, ConceptProgress.learned_at)
                    .where(ConceptProgress.concept_id.in_(active_ids))
                )
            ).all()
            progress_rows = [dict(r._mapping) for r in rows]

        attempt_rows: list[dict] = []
        if active_ids:
            rows = (
                await self.db.execute(
                    select(
                        AssessmentAttempt.user_id,
                        AssessmentItem.concept_id,
                        AssessmentAttempt.answer_text,
                        AssessmentAttempt.correct,
                        Distractor.misconception_label,
                        AssessmentAttempt.created_at,
                    )
                    .join(AssessmentItem, AssessmentItem.id == AssessmentAttempt.item_id)
                    .join(
                        Distractor,
                        Distractor.id == AssessmentAttempt.matched_distractor_id,
                        isouter=True,
                    )
                    .where(
                        AssessmentAttempt.path_id == path_id,
                        AssessmentItem.concept_id.in_(active_ids),
                    )
                )
            ).all()
            attempt_rows = [dict(r._mapping) for r in rows]

        user_ids = {r["user_id"] for r in progress_rows} | {a["user_id"] for a in attempt_rows}
        users: dict[str, dict] = {}
        if user_ids:
            rows = (
                await self.db.execute(
                    select(User.id, User.handle, User.display_name).where(User.id.in_(user_ids))
                )
            ).all()
            users = {r.id: dict(r._mapping) for r in rows}

        result = build_analytics(
            active_concepts=[{"id": c.id, "title": c.title, "position": c.position} for c in active],
            progress_rows=progress_rows,
            attempt_rows=attempt_rows,
            users=users,
        )
        result["path_id"] = path_id
        return result

    async def grade_attempt(
        self,
        path_id: str,
        concept_id: str,
        item_id: str,
        user: User,
        answer: str,
    ) -> dict:
        # Validates concept ∈ path (OQ-38) — the previous readable-path check
        # alone let an item be graded (and would let attempts be recorded)
        # against any readable path's id.
        await self._get_readable_concept_id(path_id, concept_id, user)

        stmt = (
            select(AssessmentItem)
            .where(AssessmentItem.id == item_id, AssessmentItem.concept_id == concept_id)
            .options(selectinload(AssessmentItem.distractors))
        )
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assessment item not found")

        norm_answer = _normalize_answer(answer)
        correct = norm_answer == _normalize_answer(item.correct_answer)
        feedback: str | None = None
        matched_distractor_id: str | None = None
        if not correct:
            matched_distractor_id, feedback = _match_distractor(norm_answer, item.distractors)

        # Every attempt is a row (OQ-37) — the response shape is unchanged.
        self.db.add(
            AssessmentAttempt(
                item_id=item.id,
                path_id=path_id,
                user_id=user.id,
                answer_text=answer,
                correct=correct,
                matched_distractor_id=matched_distractor_id,
            )
        )
        await self.db.commit()

        return {
            "correct": correct,
            "correct_answer": item.correct_answer if not correct else None,
            "grounding_passage_id": item.grounding_passage_id,
            "feedback": feedback,
        }
