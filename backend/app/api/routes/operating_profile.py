from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps.project import get_project_for_user
from app.db.models import CompanyOperatingProfile, Project
from app.db.session import get_db
from app.services.memory_hooks import on_blueprint_updated
from app.services.operating_profile import (
    get_or_create_operating_profile,
    operating_profile_to_dict,
    sync_operating_profile_from_blueprint,
)

router = APIRouter()


class OperatingProfileResponse(BaseModel):
    id: str
    project_id: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_model: Optional[str] = None
    target_audience: Optional[str] = None
    value_proposition: Optional[str] = None
    market_positioning: Optional[str] = None
    products_services: List[Dict[str, Any]] = []
    competitors: List[Dict[str, Any]] = []
    customer_segments: List[Any] = []
    revenue_model: Optional[str] = None
    pricing: Dict[str, Any] = {}
    team_structure: Dict[str, Any] = {}
    team_size: Optional[str] = None
    budget: Optional[str] = None
    geography: Optional[str] = None
    tech_stack: Optional[str] = None
    marketing_strategy: Optional[str] = None
    sales_strategy: Optional[str] = None
    marketing_assets: List[Any] = []
    technical_assets: List[Any] = []
    current_goals: List[Any] = []
    current_problems: List[Any] = []
    product_roadmap: List[Any] = []
    risks: List[Any] = []
    brand_voice: Optional[str] = None
    growth_stage: Optional[str] = None
    operating_mode: str = "startup"
    discovery_confidence: float = 0.0
    version: int = 1
    last_synced_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class OperatingProfileUpdate(BaseModel):
    market_positioning: Optional[str] = None
    customer_segments: Optional[List[Any]] = None
    marketing_assets: Optional[List[Any]] = None
    technical_assets: Optional[List[Any]] = None
    risks: Optional[List[Any]] = None
    team_structure: Optional[Dict[str, Any]] = None


@router.get("/projects/{project_id}/operating-profile", response_model=OperatingProfileResponse)
async def get_operating_profile(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    profile, _ = await sync_operating_profile_from_blueprint(db, project.id)
    return OperatingProfileResponse(**operating_profile_to_dict(profile))


@router.put("/projects/{project_id}/operating-profile", response_model=OperatingProfileResponse)
async def update_operating_profile(
    update: OperatingProfileUpdate,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_operating_profile(db, project.id)
    updated_fields: List[str] = []
    data = update.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(profile, field, value)
        updated_fields.append(field)
        if isinstance(value, (list, dict)):
            flag_modified(profile, field)

    profile.last_updated = datetime.utcnow()
    profile.version = (profile.version or 1) + 1
    await db.commit()
    await db.refresh(profile)

    if updated_fields:
        await on_blueprint_updated(project.id, updated_fields)

    return OperatingProfileResponse(**operating_profile_to_dict(profile))
