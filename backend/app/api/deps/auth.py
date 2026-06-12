from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_clerk_token
from app.db.models import User
from app.db.session import get_db
from app.services.founder_profile import get_or_create_founder_profile

bearer_scheme = HTTPBearer(auto_error=False)

DEV_MOCK_CLERK_ID = "dev_mock_clerk_id"
DEV_MOCK_EMAIL = "founder@dev.local"


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.clerk_id == DEV_MOCK_CLERK_ID))
    user = result.scalars().first()
    if user:
        return user
    user = User(clerk_id=DEV_MOCK_CLERK_ID, email=DEV_MOCK_EMAIL)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await get_or_create_founder_profile(db, user)
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not settings.AUTH_REQUIRED:
        if settings.DEV_MOCK_USER_ENABLED:
            return await _get_or_create_dev_user(db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    claims = await verify_clerk_token(credentials.credentials)
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    email = claims.get("email") or claims.get("primary_email_address") or f"{clerk_id}@clerk.local"

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalars().first()
    if user:
        if user.email != email and email:
            user.email = email
            await db.commit()
            await db.refresh(user)
        return user

    user = User(clerk_id=clerk_id, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await get_or_create_founder_profile(db, user)
    return user


async def get_current_user_from_token(token: str, db: AsyncSession) -> User:
    """Validate a raw bearer token (e.g. WebSocket query param)."""
    if not settings.AUTH_REQUIRED and settings.DEV_MOCK_USER_ENABLED:
        return await _get_or_create_dev_user(db)

    claims = await verify_clerk_token(token)
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    email = claims.get("email") or f"{clerk_id}@clerk.local"
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalars().first()
    if user:
        return user

    user = User(clerk_id=clerk_id, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await get_or_create_founder_profile(db, user)
    return user
