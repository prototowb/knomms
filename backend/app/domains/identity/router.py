from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.auth import get_current_user
from app.deps.db import get_db
from app.domains.identity.service import IdentityService
from app.models.user import User
from app.schemas.user import RefreshRequest, TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc = IdentityService(db)
    _user, tokens = await svc.register(body)
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc = IdentityService(db)
    _user, tokens = await svc.login(body)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc = IdentityService(db)
    return await svc.refresh(body.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    out = UserOut.model_validate(current_user)
    if current_user.org_id is not None:
        from app.models.organisation import Organisation

        org = await db.get(Organisation, current_user.org_id)
        out.org_name = org.name if org else None
    return out
