import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenResponse, UserLogin, UserRegister


class IdentityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: UserRegister) -> tuple[User, TokenResponse]:
        # Check uniqueness
        existing = await self.db.execute(
            select(User).where((User.email == data.email) | (User.handle == data.handle))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Email or handle already in use"
            )

        user = User(
            id=str(uuid.uuid4()),
            email=data.email,
            handle=data.handle,
            display_name=data.display_name,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()  # get the id without committing

        tokens = self._issue_tokens(user)
        return user, tokens

    async def login(self, data: UserLogin) -> tuple[User, TokenResponse]:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Account inactive")

        return user, self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Expected refresh token")

        user = await self.db.get(User, payload["sub"])
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        # For now, namespaces = user's own private KB namespace sentinel.
        # Expanded in later milestones when KBs are created.
        namespaces: list[str] = [f"user:{user.id}"]
        return TokenResponse(
            access_token=create_access_token(user.id, namespaces),
            refresh_token=create_refresh_token(user.id),
        )
