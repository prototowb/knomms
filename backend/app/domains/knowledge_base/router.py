from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user, get_optional_user
from app.deps.db import get_db
from app.domains.knowledge_base.service import KnowledgeBaseService
from app.models.source import Source
from app.models.user import User
from app.schemas.knowledge_base import ChunkSearchResult, KnowledgeBaseOut, PublicKBOut
from app.schemas.source import SourceStatusOut

router = APIRouter(prefix="/kbs", tags=["knowledge-bases"])


class CreateKBRequest(BaseModel):
    title: str
    visibility: str = "private"


class UpdateKBRequest(BaseModel):
    title: str | None = None
    visibility: str | None = None


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_kbs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[KnowledgeBaseOut]:
    svc = KnowledgeBaseService(db)
    kbs = await svc.list_for_user(user)
    return [KnowledgeBaseOut.model_validate(kb) for kb in kbs]


@router.get(
    "/public",
    response_model=list[PublicKBOut],
    summary="List public knowledge bases (no auth required — explore surface)",
)
async def list_public_kbs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
) -> list[PublicKBOut]:
    svc = KnowledgeBaseService(db)
    kbs = await svc.list_public(limit=limit, offset=offset)
    return [PublicKBOut.model_validate(kb) for kb in kbs]


@router.get(
    "/org",
    response_model=list[PublicKBOut],
    summary="List your organisation's team-visible knowledge bases (explore surface)",
)
async def list_org_kbs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PublicKBOut]:
    svc = KnowledgeBaseService(db)
    kbs = await svc.list_org(user, limit=limit, offset=offset)
    return [PublicKBOut.model_validate(kb) for kb in kbs]


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_kb(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_readable_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return KnowledgeBaseOut.model_validate(kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut, summary="Update KB metadata (owner only)")
async def update_kb(
    kb_id: str,
    req: UpdateKBRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    from app.domains.knowledge_base.service import VISIBILITIES

    svc = KnowledgeBaseService(db)
    kb = await svc.get_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    if req.title is not None:
        kb.title = req.title
    if req.visibility is not None:
        if req.visibility not in VISIBILITIES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"visibility must be one of: {sorted(VISIBILITIES)}",
            )
        kb.visibility = req.visibility
    await db.commit()
    kb = await svc.get_by_id(kb_id, user)
    return KnowledgeBaseOut.model_validate(kb)


@router.get("/{kb_id}/sources", response_model=list[SourceStatusOut])
async def list_kb_sources(
    kb_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SourceStatusOut]:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_readable_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    # KB visibility is the access boundary — Source.visibility is dormant by
    # design; the old owner clause hid every source from team/public readers.
    result = await db.execute(
        select(Source)
        .where(Source.kb_id == kb_id)
        .order_by(Source.created_at.desc())
        .limit(limit)
    )
    return [SourceStatusOut.model_validate(s) for s in result.scalars().all()]


@router.get(
    "/{kb_id}/search",
    response_model=list[ChunkSearchResult],
    summary="Search within a KB's sources — semantic (pgvector) or keyword (FTS)",
)
async def search_kb(
    kb_id: str,
    q: str = Query(min_length=2),
    mode: str = Query("semantic", pattern="^(semantic|keyword)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChunkSearchResult]:
    svc = KnowledgeBaseService(db)
    kb = await svc.get_readable_by_id(kb_id, user)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    if mode == "keyword":
        from sqlalchemy import func

        from app.models.chunk import Chunk

        tsvector = func.to_tsvector("english", Chunk.text)
        tsquery = func.plainto_tsquery("english", q)
        result = await db.execute(
            select(Chunk, func.ts_rank(tsvector, tsquery).label("rank"))
            .where(
                Chunk.vector_namespace == kb.vector_namespace,
                tsvector.op("@@")(tsquery),
            )
            .order_by(func.ts_rank(tsvector, tsquery).desc())
            .limit(limit)
        )
        rows = result.all()
        # score is ts_rank here (higher = better), cosine distance in
        # semantic mode (lower = better) — clients sort by list order.
        hits = [
            (chunk.id, chunk.source_id, chunk.locator, chunk.text, float(rank))
            for chunk, rank in rows
        ]
    else:
        from app.domains.generation.ollama import embed
        from app.domains.retrieval.service import RetrievalService

        query_vec = (await embed([q]))[0]
        chunks = await RetrievalService(db).retrieve(query_vec, kb.vector_namespace, top_k=limit)
        hits = [(c.chunk_id, c.source_id, c.locator, c.text, c.score) for c in chunks]

    source_ids = {h[1] for h in hits}
    sources = {}
    if source_ids:
        result = await db.execute(select(Source).where(Source.id.in_(source_ids)))
        sources = {s.id: s for s in result.scalars().all()}

    return [
        ChunkSearchResult(
            chunk_id=chunk_id,
            source_id=source_id,
            source_title=sources[source_id].title if source_id in sources else "(unknown source)",
            source_type=sources[source_id].type if source_id in sources else "unknown",
            locator=locator,
            text=text,
            score=score,
        )
        for chunk_id, source_id, locator, text, score in hits
    ]


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
async def create_kb(
    req: CreateKBRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    svc = KnowledgeBaseService(db)
    kb = await svc.create(user, req.title, visibility=req.visibility)
    await db.commit()
    # Re-fetch with owner eager-loaded — model_validate would otherwise lazy-load
    # the relationship, which raises on an async session.
    kb = await svc.get_by_id(kb.id, user)
    return KnowledgeBaseOut.model_validate(kb)
