from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps.auth import get_current_user
from app.db.models import FounderProfile, User
from app.db.session import get_db
from app.services.founder_profile import get_or_create_founder_profile

router = APIRouter()


class FounderProfileResponse(BaseModel):
    id: str
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    timezone: str = "UTC"
    expertise: List[str] = []
    preferences: Dict[str, Any] = {}
    founding_goals: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FounderProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    expertise: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None
    founding_goals: Optional[List[str]] = None


@router.get("/founder-profile", response_model=FounderProfileResponse)
async def get_my_founder_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_founder_profile(db, current_user)
    return profile


@router.put("/founder-profile", response_model=FounderProfileResponse)
async def update_my_founder_profile(
    update: FounderProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_founder_profile(db, current_user)
    data = update.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(profile, field, value)
        if isinstance(value, (list, dict)):
            flag_modified(profile, field)

    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return profile
