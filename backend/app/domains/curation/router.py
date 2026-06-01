from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user, get_optional_user
from app.deps.db import get_db
from app.domains.curation.service import BoardService
from app.models.user import User
from pydantic import BaseModel as _BaseModel

from app.schemas.curation import (
    AddSourceRequest,
    BoardItemOut,
    BoardOut,
    BoardSummary,
    CreateBoardRequest,
    CuratorProfileOut,
    ForkBoardRequest,
)


class UpdateBoardRequest(_BaseModel):
    title: str | None = None
    description: str | None = None
    visibility: str | None = None
    layout_config: dict | None = None

router = APIRouter(tags=["curation"])


def _board_to_out(board) -> BoardOut:
    return BoardOut(
        id=board.id,
        title=board.title,
        description=board.description,
        visibility=board.visibility,
        fork_count=board.fork_count,
        forked_from_id=board.forked_from_id,
        fork_lineage=board.fork_lineage or [],
        layout_config=board.layout_config or {},
        ai_summary=board.ai_summary,
        item_count=len(board.items) if hasattr(board, "items") else 0,
        created_at=board.created_at,
        updated_at=board.updated_at,
        owner=board.owner if hasattr(board, "owner") and board.owner else None,
        items=[BoardItemOut.model_validate(i) for i in (board.items or [])],
    )


def _board_to_summary(board) -> BoardSummary:
    item_count = len(board.items) if hasattr(board, "items") and board.items else 0
    return BoardSummary(
        id=board.id,
        title=board.title,
        description=board.description,
        visibility=board.visibility,
        fork_count=board.fork_count,
        item_count=item_count,
        ai_summary=board.ai_summary,
        created_at=board.created_at,
        owner=board.owner if hasattr(board, "owner") and board.owner else None,
    )


@router.get("/boards", response_model=list[BoardSummary], summary="List public boards")
async def list_boards(
    sort: str = Query("trending", pattern="^(trending|recent)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
) -> list[BoardSummary]:
    svc = BoardService(db)
    boards = await svc.list_public_boards(sort=sort, limit=limit, offset=offset)
    return [_board_to_summary(b) for b in boards]


@router.get("/boards/search", response_model=list[BoardSummary], summary="Semantic board search")
async def search_boards(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
) -> list[BoardSummary]:
    svc = BoardService(db)
    boards = await svc.search_boards_semantic(q, limit=limit)
    return [_board_to_summary(b) for b in boards]


@router.get("/boards/{board_id}", response_model=BoardOut, summary="Get a public board")
async def get_board(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
) -> BoardOut:
    svc = BoardService(db)
    board = await svc.get_public_board(board_id)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    return _board_to_out(board)


@router.post("/boards", response_model=BoardOut, status_code=201, summary="Create a board")
async def create_board(
    req: CreateBoardRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BoardOut:
    svc = BoardService(db)
    board = await svc.create_board(
        user, req.title, req.description, req.visibility, req.layout_config or None
    )
    board = await svc.get_board_for_owner(board.id, user)
    return _board_to_out(board)


@router.post("/boards/{board_id}/fork", response_model=BoardOut, status_code=201, summary="Fork a public board")
async def fork_board(
    board_id: str,
    req: ForkBoardRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BoardOut:
    svc = BoardService(db)
    fork = await svc.fork_board(board_id, user, req.new_title, req.visibility)
    fork = await svc.get_board_for_owner(fork.id, user)
    return _board_to_out(fork)


@router.post(
    "/boards/{board_id}/sources",
    response_model=BoardItemOut,
    status_code=201,
    summary="Add a URL source to a board",
)
async def add_source(
    board_id: str,
    req: AddSourceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BoardItemOut:
    svc = BoardService(db)
    item = await svc.add_source_to_board(board_id, user, req.source_url, req.note, req.lane)
    return BoardItemOut.model_validate(item)


@router.post(
    "/boards/{board_id}/generate-summary",
    summary="Generate an AI board summary",
)
async def generate_summary(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = BoardService(db)
    summary = await svc.generate_board_summary(board_id, user)
    return {"summary": summary}


@router.get("/my/boards", response_model=list[BoardSummary], summary="List the current user's boards")
async def list_my_boards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BoardSummary]:
    svc = BoardService(db)
    boards = await svc.list_my_boards(user)
    return [_board_to_summary(b) for b in boards]


@router.patch("/boards/{board_id}", response_model=BoardOut, summary="Update board metadata")
async def update_board(
    board_id: str,
    req: UpdateBoardRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BoardOut:
    svc = BoardService(db)
    board = await svc.get_board_for_owner(board_id, user)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    if req.title is not None:
        board.title = req.title
    if req.description is not None:
        board.description = req.description
    if req.visibility is not None:
        if req.visibility not in ("private", "team", "public"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid visibility")
        board.visibility = req.visibility
    if req.layout_config is not None:
        board.layout_config = req.layout_config
    await db.commit()
    board = await svc.get_board_for_owner(board_id, user)
    return _board_to_out(board)


@router.get("/u/{handle}", response_model=CuratorProfileOut, summary="Get curator profile")
async def get_curator_profile(
    handle: str,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_optional_user),
) -> CuratorProfileOut:
    svc = BoardService(db)
    result = await svc.get_curator_profile(handle)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Curator not found")
    profile_user, boards = result
    return CuratorProfileOut(
        handle=profile_user.handle,
        display_name=profile_user.display_name,
        board_count=len(boards),
        boards=[_board_to_summary(b) for b in boards],
    )
