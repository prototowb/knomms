"""Learning service — DB operations for learning paths."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.knowledge_base.service import KnowledgeBaseService
from app.domains.learning.agent import build_concept_groups, generate_curriculum
from app.models.chunk import Chunk
from app.models.learning import AssessmentItem, Distractor, LearningPath, PathConcept
from app.models.user import User


class LearningService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_draft(
        self,
        kb_id: str,
        user: User,
        learning_goal: str,
        time_budget_hours: float | None,
    ) -> LearningPath:
        kb_svc = KnowledgeBaseService(self.db)
        kb = await kb_svc.get_by_id(kb_id, user)
        if kb is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        # Load all non-overlap, embedded chunks for this KB in sequence order
        stmt = (
            select(
                Chunk.id,
                Chunk.source_id,
                Chunk.locator,
                Chunk.text,
                Chunk.is_overlap,
                Chunk.seq,
            )
            .where(
                Chunk.vector_namespace == kb.vector_namespace,
                Chunk.embedding.is_not(None),
            )
            .order_by(Chunk.source_id, Chunk.seq)
        )
        rows = (await self.db.execute(stmt)).mappings().all()
        chunks = [dict(r) for r in rows]

        if not chunks:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Knowledge base has no indexed chunks — ingest a source first",
            )

        groups = build_concept_groups(chunks)
        proposals = await generate_curriculum(groups)

        if not proposals:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Curriculum agent could not generate any grounded concepts from this corpus",
            )

        path = LearningPath(
            kb_id=kb_id,
            user_id=user.id,
            learning_goal=learning_goal,
            time_budget_hours=time_budget_hours,
        )
        self.db.add(path)
        await self.db.flush()

        for pos, proposal in enumerate(proposals):
            concept = PathConcept(
                path_id=path.id,
                position=pos,
                title=proposal.title,
                explanation_text=proposal.explanation_text,
                explanation_passage_ids=proposal.passage_ids_cited,
                source_passages=[
                    {
                        "chunk_id": p.chunk_id,
                        "locator": p.locator,
                        "source_id": p.source_id,
                        "excerpt": p.text[:300],
                    }
                    for p in proposal.source_passages
                ],
            )
            self.db.add(concept)
            await self.db.flush()

            if proposal.assessment:
                a = proposal.assessment
                item = AssessmentItem(
                    concept_id=concept.id,
                    question_text=a.question_text,
                    grounding_passage_id=a.grounding_chunk_id,
                    correct_answer=a.correct_answer,
                )
                self.db.add(item)
                await self.db.flush()

                for d in a.distractors:
                    self.db.add(
                        Distractor(
                            item_id=item.id,
                            text=d.text,
                            why_wrong_passage_id=d.why_wrong_chunk_id,
                            misconception_label=d.misconception_label,
                        )
                    )

        await self.db.commit()
        return path

    async def get_path(self, path_id: str, user: User) -> LearningPath | None:
        stmt = (
            select(LearningPath)
            .where(LearningPath.id == path_id, LearningPath.user_id == user.id)
            .options(
                selectinload(LearningPath.concepts).selectinload(
                    PathConcept.assessment_items
                ).selectinload(AssessmentItem.distractors)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paths(self, kb_id: str, user: User) -> list[LearningPath]:
        stmt = (
            select(LearningPath)
            .where(LearningPath.kb_id == kb_id, LearningPath.user_id == user.id)
            .order_by(LearningPath.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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

    async def grade_attempt(
        self,
        path_id: str,
        concept_id: str,
        item_id: str,
        user: User,
        answer: str,
    ) -> dict:
        path = await self.get_path(path_id, user)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")

        stmt = (
            select(AssessmentItem)
            .where(AssessmentItem.id == item_id, AssessmentItem.concept_id == concept_id)
            .options(selectinload(AssessmentItem.distractors))
        )
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assessment item not found")

        correct = answer.strip().lower() == item.correct_answer.strip().lower()
        feedback: str | None = None
        if not correct:
            answer_lower = answer.strip().lower()
            for d in item.distractors:
                if answer_lower in d.text.lower() or d.text.lower() in answer_lower:
                    feedback = d.misconception_label
                    break

        return {
            "correct": correct,
            "correct_answer": item.correct_answer if not correct else None,
            "grounding_passage_id": item.grounding_passage_id,
            "feedback": feedback,
        }
