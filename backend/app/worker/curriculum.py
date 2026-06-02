"""Curriculum job pipeline — runs curriculum agent for a LearningPath record.

Called by the worker consumer for each curriculum.jobs message.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — ensures full ORM registry before any DB ops
from app.domains.learning.agent import build_concept_groups, generate_curriculum
from app.models.chunk import Chunk
from app.models.knowledge_base import KnowledgeBase
from app.models.learning import AssessmentItem, Distractor, LearningPath, PathConcept

logger = logging.getLogger(__name__)


async def run_curriculum_job(db: AsyncSession, job: dict) -> None:
    path_id: str = job["path_id"]
    kb_id: str = job["kb_id"]

    path = await db.get(LearningPath, path_id)
    if path is None:
        logger.error("LearningPath %s not found — skipping job", path_id)
        return

    try:
        kb = await db.get(KnowledgeBase, kb_id)
        if kb is None:
            logger.error("KnowledgeBase %s not found for path %s", kb_id, path_id)
            path.status = "failed"
            await db.commit()
            return

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
        rows = (await db.execute(stmt)).mappings().all()
        chunks = [dict(r) for r in rows]

        if not chunks:
            logger.warning("No indexed chunks for KB %s — marking path %s failed", kb_id, path_id)
            path.status = "failed"
            await db.commit()
            return

        groups = build_concept_groups(chunks)
        proposals = await generate_curriculum(groups)

        if not proposals:
            logger.warning("Curriculum agent produced no proposals for path %s", path_id)
            path.status = "failed"
            await db.commit()
            return

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
            db.add(concept)
            await db.flush()

            if proposal.assessment:
                a = proposal.assessment
                item = AssessmentItem(
                    concept_id=concept.id,
                    question_text=a.question_text,
                    grounding_passage_id=a.grounding_chunk_id,
                    correct_answer=a.correct_answer,
                )
                db.add(item)
                await db.flush()

                for d in a.distractors:
                    db.add(
                        Distractor(
                            item_id=item.id,
                            text=d.text,
                            why_wrong_passage_id=d.why_wrong_chunk_id,
                            misconception_label=d.misconception_label,
                        )
                    )

        path.status = "draft"
        await db.commit()
        logger.info("Curriculum job complete for path %s — %d concepts", path_id, len(proposals))

    except Exception:
        logger.exception("Curriculum job failed for path %s", path_id)
        try:
            path.status = "failed"
            await db.commit()
        except Exception:
            logger.exception("Could not mark path %s as failed", path_id)
        raise
