"""Harness study-KB service — project harness facets into a dedicated KB (docs/12).

One Source per facet: each slot's asset version, the eval suite's cases, and
the most recent completed eval runs. The curriculum agent groups concepts per
source (KC-074), so each facet becomes its own concept in a generated path.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import get_redis
from app.core.storage import write_object
from app.domains.harnesses.study_docs import (
    compose_eval_run_doc,
    compose_eval_suite_doc,
    compose_slot_doc,
    plan_study_projection,
)
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.asset import AssetVersion, EvalRun, Harness, HarnessAsset, HarnessStudyDoc
from app.models.knowledge_base import KnowledgeBase
from app.models.source import Source
from app.models.user import User

_INGESTION_STREAM_KEY = "ingestion.jobs"

MAX_EVAL_RUN_DOCS = 10

# Suite/run docs are synthesized plain text; slot docs carry a version's
# prompt content, same as direct asset projections (OQ-32).
_DOC_SOURCE_TYPES = {"slot": "prompt_asset", "eval_suite": "plain_text", "eval_run": "plain_text"}


class HarnessStudyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_owned_harness(self, harness_id: str, user: User) -> Harness:
        """Owner-only, 404 for everyone else (OQ-34) — the study KB projects
        slot contents and eval outputs, so its existence must not leak through
        public/team harnesses (same contract as eval-run reads)."""
        harness = await self.db.get(Harness, harness_id)
        if harness is None or harness.owner_user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Harness not found")
        return harness

    async def project(self, harness_id: str, user: User) -> dict:
        """Create-or-refresh the harness's study KB (docs/12, OQ-33).

        Ensures the KB exists, projects any facet docs not yet present,
        re-enqueues docs whose previous ingestion failed, and returns
        {kb_id, projected, skipped}.
        """
        harness = await self._get_owned_harness(harness_id, user)
        harness_title = harness.title

        slots = (
            await self.db.execute(
                select(HarnessAsset)
                .where(HarnessAsset.harness_id == harness_id)
                .order_by(HarnessAsset.position, HarnessAsset.added_at)
                .options(
                    selectinload(HarnessAsset.asset_version).selectinload(AssetVersion.asset),
                    selectinload(HarnessAsset.asset_version).selectinload(AssetVersion.eval_cases),
                )
            )
        ).scalars().all()

        runs = (
            await self.db.execute(
                select(EvalRun)
                .where(
                    EvalRun.harness_id == harness_id,
                    EvalRun.status == "completed",
                    EvalRun.metrics.is_not(None),
                )
                .order_by(EvalRun.created_at.desc())
                .limit(MAX_EVAL_RUN_DOCS)
            )
        ).scalars().all()

        if not slots and not runs:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nothing to study — add asset slots or complete an eval run first",
            )

        # Desired facet docs, in projection order: (kind, ref_id) → (title, content)
        docs: dict[tuple[str, str], tuple[str, str]] = {}
        for slot in slots:
            version = slot.asset_version
            asset = version.asset
            docs.setdefault(
                ("slot", version.id),
                (
                    f"Slot: {slot.role} — {asset.title} v{version.version_num}",
                    compose_slot_doc(
                        role=slot.role,
                        asset_title=asset.title,
                        asset_description=asset.description,
                        version_num=version.version_num,
                        model_pin=version.model_pin,
                        rationale=version.rationale,
                        content=version.content,
                    ),
                ),
            )
            if slot.role == "eval_suite" and version.eval_cases:
                docs.setdefault(
                    ("eval_suite", version.id),
                    (
                        f"Eval suite: {asset.title} v{version.version_num}",
                        compose_eval_suite_doc(
                            harness_title=harness_title,
                            asset_title=asset.title,
                            version_num=version.version_num,
                            cases=[
                                {
                                    "input": c.input,
                                    "expected_output": c.expected_output,
                                    "grading_strategy": c.grading_strategy,
                                }
                                for c in version.eval_cases
                            ],
                        ),
                    ),
                )
        for run in runs:
            run_date = run.created_at.date().isoformat()
            docs[("eval_run", run.id)] = (
                f"Eval run: {run.model_pin} — {run_date}",
                compose_eval_run_doc(
                    harness_title=harness_title,
                    model_pin=run.model_pin,
                    provider=run.provider,
                    created_at=run_date,
                    metrics=run.metrics,
                ),
            )

        # Resolve-or-create the study KB. Always private (OQ-34): slots may
        # reference versions shared with the owner via grants — mirroring a
        # public harness's visibility here would republish that content.
        kb: KnowledgeBase | None = None
        if harness.study_kb_id:
            kb = await self.db.get(KnowledgeBase, harness.study_kb_id)
        if kb is None:
            kb = await KnowledgeBaseService(self.db).create(
                user, title=f"Study: {harness_title}", visibility="private"
            )
            harness.study_kb_id = kb.id
        kb_id, vector_namespace = kb.id, kb.vector_namespace
        user_id = user.id

        existing_rows = (
            await self.db.execute(
                select(
                    HarnessStudyDoc.doc_kind,
                    HarnessStudyDoc.ref_id,
                    HarnessStudyDoc.source_id,
                    Source.ingestion_status,
                )
                .join(Source, Source.id == HarnessStudyDoc.source_id)
                .where(HarnessStudyDoc.kb_id == kb_id)
            )
        ).all()
        existing_status = {(r.doc_kind, r.ref_id): r.ingestion_status for r in existing_rows}
        existing_source = {(r.doc_kind, r.ref_id): r.source_id for r in existing_rows}

        plan = plan_study_projection(list(docs.keys()), existing_status)

        to_enqueue: list[tuple[str, str, str]] = []  # (source_id, storage_key, content)

        created_doc_rows: list[HarnessStudyDoc] = []
        for key in plan["create"]:
            kind, ref_id = key
            title, content = docs[key]
            source_id = str(uuid.uuid4())
            storage_key = f"raw/{user_id}/{source_id}/study-doc.md"
            self.db.add(
                Source(
                    id=source_id,
                    owner_user_id=user_id,
                    type=_DOC_SOURCE_TYPES[kind],
                    storage_key=storage_key,
                    title=title,
                    kb_id=kb_id,
                    ingestion_status="pending",
                )
            )
            created_doc_rows.append(
                HarnessStudyDoc(
                    harness_id=harness_id,
                    kb_id=kb_id,
                    doc_kind=kind,
                    ref_id=ref_id,
                    source_id=source_id,
                )
            )
            to_enqueue.append((source_id, storage_key, content))

        # Sources must hit the DB before the doc rows that reference them —
        # there is no ORM relationship between the two, so the unit of work
        # will not order the inserts itself (project_version precedent).
        if created_doc_rows:
            await self.db.flush()
            self.db.add_all(created_doc_rows)

        for key in plan["reenqueue"]:
            source = await self.db.get(Source, existing_source[key])
            source.ingestion_status = "pending"
            storage_key = source.storage_key or f"raw/{user_id}/{source.id}/study-doc.md"
            source.storage_key = storage_key
            to_enqueue.append((source.id, storage_key, docs[key][1]))

        # Commit BEFORE enqueueing (OQ-36) — the worker must never pick up a
        # job whose Source row isn't visible yet.
        await self.db.commit()

        redis = await get_redis()
        for source_id, storage_key, content in to_enqueue:
            data = content.encode("utf-8")
            # Dual-write: MinIO for durability past the Redis TTL, Redis for
            # fast worker pickup (add_file_to_board precedent).
            await write_object(settings.minio_bucket, storage_key, data, content_type="text/markdown")
            await redis.setex(f"upload:{source_id}", 3600, data)
            await redis.xadd(
                _INGESTION_STREAM_KEY,
                {
                    "source_id": source_id,
                    "user_id": user_id,
                    "kb_id": kb_id,
                    "vector_namespace": vector_namespace,
                    "upload": "1",
                },
            )

        return {
            "kb_id": kb_id,
            "projected": len(plan["create"]) + len(plan["reenqueue"]),
            "skipped": plan["skipped"],
        }

    async def get_status(self, harness_id: str, user: User) -> dict:
        """Per-doc ingestion status for the frontend poll. 404 until the first
        projection (owner-only, same non-leak contract as project())."""
        harness = await self._get_owned_harness(harness_id, user)
        if not harness.study_kb_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No study KB for this harness yet")

        rows = (
            await self.db.execute(
                select(
                    HarnessStudyDoc.doc_kind,
                    HarnessStudyDoc.ref_id,
                    HarnessStudyDoc.source_id,
                    Source.title,
                    Source.ingestion_status,
                )
                .join(Source, Source.id == HarnessStudyDoc.source_id)
                .where(HarnessStudyDoc.kb_id == harness.study_kb_id)
                .order_by(HarnessStudyDoc.created_at, HarnessStudyDoc.id)
            )
        ).all()

        return {
            "kb_id": harness.study_kb_id,
            "docs": [
                {
                    "doc_kind": r.doc_kind,
                    "ref_id": r.ref_id,
                    "source_id": r.source_id,
                    "title": r.title,
                    "ingestion_status": r.ingestion_status,
                }
                for r in rows
            ],
        }
