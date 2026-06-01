from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.generation.service import GenerationService
from app.models.user import User

router = APIRouter(prefix="/kbs", tags=["generation"])


class QueryRequest(BaseModel):
    query: str


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
