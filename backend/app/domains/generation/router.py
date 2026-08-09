from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.generation.service import GenerationService
from app.models.user import User
from app.schemas.synthesis import SaveSynthesisRequest, SynthesisOut

router = APIRouter(prefix="/kbs", tags=["generation"])


class QueryRequest(BaseModel):
    query: str


class SynthesizeRequest(BaseModel):
    question: str
    source_ids: list[str]


@router.post("/{kb_id}/query")
async def query_knowledge_base(
    kb_id: str,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Grounded Q&A with SSE streaming. Matches useStreamingQuery.ts contract:
      event 1:  event: citations\\ndata: <JSON>\\n\\n
      events N: data: <token>\\n\\n
    """
    svc = GenerationService(db)
    response_stream = await svc.stream_grounded_response(kb_id, body.query, current_user)
    return StreamingResponse(
        response_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )


@router.post("/{kb_id}/syntheses", status_code=201)
async def save_synthesis(
    kb_id: str,
    body: SaveSynthesisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SynthesisOut:
    """Save a completed synthesis as the author's record (docs/17, OQ-70)."""
    from app.domains.generation.synthesis import SynthesisService

    row = await SynthesisService(db).save(
        kb_id,
        current_user,
        question=body.question,
        answer_text=body.answer_text,
        source_ids=body.source_ids,
        citations=[c.model_dump() for c in body.citations],
    )
    return SynthesisOut.model_validate(row)


@router.get("/{kb_id}/syntheses")
async def list_syntheses(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SynthesisOut]:
    """The current user's saved syntheses on this KB, newest first."""
    from app.domains.generation.synthesis import SynthesisService

    rows = await SynthesisService(db).list_for_kb(kb_id, current_user)
    return [SynthesisOut.model_validate(r) for r in rows]


@router.delete("/{kb_id}/syntheses/{synthesis_id}", status_code=204)
async def delete_synthesis(
    kb_id: str,
    synthesis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    from app.domains.generation.synthesis import SynthesisService

    await SynthesisService(db).delete(kb_id, synthesis_id, current_user)


@router.post("/{kb_id}/synthesize")
async def synthesize_sources(
    kb_id: str,
    body: SynthesizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Comparative synthesis across selected sources (docs/16) — same SSE
    contract as /query, so clients reuse the streaming composable."""
    from app.domains.generation.synthesis import SynthesisService

    svc = SynthesisService(db)
    response_stream = await svc.stream_synthesis(
        kb_id, body.question, body.source_ids, current_user
    )
    return StreamingResponse(
        response_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
