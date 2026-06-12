"""Founder profile provisioning and helpers."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FounderProfile, User


async def get_or_create_founder_profile(db: AsyncSession, user: User) -> FounderProfile:
    result = await db.execute(select(FounderProfile).where(FounderProfile.user_id == user.id))
    profile = result.scalars().first()
    if profile:
        return profile

    display_name = user.email.split("@")[0] if user.email else "Founder"
    profile = FounderProfile(
        user_id=user.id,
        display_name=display_name,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_founder_profile(db: AsyncSession, user_id: str) -> Optional[FounderProfile]:
    result = await db.execute(select(FounderProfile).where(FounderProfile.user_id == user_id))
    return result.scalars().first()
