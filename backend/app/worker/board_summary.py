"""Board summary job — generates the AI summary for a board asynchronously (KC-030).

Called by the worker consumer for each board.summary.jobs message.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.models  # noqa: F401 — ensures full ORM registry before any DB ops
from app.domains.curation.service import _SUMMARY_PROMPT
from app.models.collection import Collection, CollectionItem

logger = logging.getLogger(__name__)


async def run_board_summary_job(db: AsyncSession, job: dict) -> None:
    board_id: str = job["board_id"]

    board = (
        await db.execute(
            select(Collection)
            .where(Collection.id == board_id)
            .options(selectinload(Collection.items).selectinload(CollectionItem.source))
        )
    ).scalar_one_or_none()
    if board is None:
        logger.error("Board %s not found — skipping summary job", board_id)
        return

    try:
        source_lines = "\n".join(
            f"  - {item.source.title}: {item.note or item.source.description[:100]}"
            for item in board.items
            if item.source
        )
        prompt = _SUMMARY_PROMPT.format(
            title=board.title,
            description=board.description or "(none)",
            count=len(board.items),
            source_list=source_lines or "  (no sources yet)",
        )

        from app.domains.generation.ollama import generate

        summary = await generate(prompt)
        board.ai_summary = summary.strip()
        board.summary_status = "ready"
        await db.commit()
        logger.info("Board %s summary generated (%d chars)", board_id, len(board.ai_summary))

    except Exception:
        logger.exception("Board summary job failed for board %s", board_id)
        try:
            # Rollback any partial state before marking failed, otherwise a
            # retry would work against an inconsistent session.
            await db.rollback()
            board.summary_status = "failed"
            await db.commit()
        except Exception:
            logger.exception("Could not mark board %s summary as failed", board_id)
        raise
