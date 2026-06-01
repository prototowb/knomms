from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.core.security import decode_token
from app.deps.db import get_db
from app.models.user import User

bearer = HTTPBearer()
_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Expected access token")

    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Attach resolved namespaces to the user object for use in retrieval queries
    user._namespaces = payload.get("namespaces", [])  # type: ignore[attr-defined]
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return the current user if a valid Bearer token is present; otherwise None.

    Used by public endpoints (board view, explore, curator profiles) that are
    accessible without authentication but can personalize responses when authed.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    if payload.get("type") != "access":
        return None
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        return None
    return user
