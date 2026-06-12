# backend/app/api/routes/blueprint.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, CompanyBlueprint

router = APIRouter()


# ─── Pydantic Schemas ───

class BlueprintResponse(BaseModel):
    id: str
    project_id: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_model: Optional[str] = None
    target_audience: Optional[str] = None
    value_proposition: Optional[str] = None
    products_services: List[Dict[str, Any]] = []
    competitors: List[Dict[str, Any]] = []
    revenue_model: Optional[str] = None
    pricing: Dict[str, Any] = {}
    team_size: Optional[str] = None
    budget: Optional[str] = None
    geography: Optional[str] = None
    tech_stack: Optional[str] = None
    marketing_strategy: Optional[str] = None
    sales_strategy: Optional[str] = None
    current_goals: List[str] = []
    current_problems: List[str] = []
    product_roadmap: List[Dict[str, Any]] = []
    brand_voice: Optional[str] = None
    growth_stage: Optional[str] = None
    discovery_confidence: float = 0.0
    field_confidences: Dict[str, float] = {}
    last_updated: Optional[datetime] = None
    version: int = 1

    class Config:
        from_attributes = True


class BlueprintUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_model: Optional[str] = None
    target_audience: Optional[str] = None
    value_proposition: Optional[str] = None
    products_services: Optional[List[Dict[str, Any]]] = None
    competitors: Optional[List[Dict[str, Any]]] = None
    revenue_model: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    team_size: Optional[str] = None
    budget: Optional[str] = None
    geography: Optional[str] = None
    tech_stack: Optional[str] = None
    marketing_strategy: Optional[str] = None
    sales_strategy: Optional[str] = None
    current_goals: Optional[List[str]] = None
    current_problems: Optional[List[str]] = None
    product_roadmap: Optional[List[Dict[str, Any]]] = None
    brand_voice: Optional[str] = None
    growth_stage: Optional[str] = None


# ─── Endpoints ───

@router.get("/projects/{project_id}/blueprint", response_model=BlueprintResponse)
async def get_blueprint(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the company blueprint for a project. Creates one if it doesn't exist."""
    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project.id)
    )
    blueprint = result.scalars().first()

    if not blueprint:
        ctx = project.core_context or {}
        blueprint = CompanyBlueprint(
            project_id=project.id,
            company_name=ctx.get("company_name", project.name),
            value_proposition=ctx.get("value_proposition"),
            target_audience=ctx.get("target_audience"),
            tech_stack=ctx.get("tech_stack"),
            business_model=ctx.get("business_model"),
        )
        db.add(blueprint)
        await db.commit()
        await db.refresh(blueprint)

    return blueprint


@router.put("/projects/{project_id}/blueprint", response_model=BlueprintResponse)
async def update_blueprint(
    update: BlueprintUpdate,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Update specific fields of the company blueprint."""
    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project.id)
    )
    blueprint = result.scalars().first()

    if not blueprint:
        blueprint = CompanyBlueprint(project_id=project.id)
        db.add(blueprint)

    # Apply only non-None fields
    update_data = update.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(blueprint, field, value)

    blueprint.version = (blueprint.version or 1) + 1
    blueprint.last_updated = datetime.utcnow()

    from sqlalchemy.orm.attributes import flag_modified
    for json_field in ["products_services", "competitors", "pricing", "current_goals", "current_problems", "product_roadmap"]:
        if json_field in update_data:
            flag_modified(blueprint, json_field)

    await db.commit()
    await db.refresh(blueprint)

    from app.services.memory_hooks import on_blueprint_updated
    await on_blueprint_updated(project.id, list(update_data.keys()))
    return blueprint


@router.get("/projects/{project_id}/blueprint/export")
async def export_blueprint(project: Project = Depends(get_project_for_user), db: AsyncSession = Depends(get_db)):
    """Export the blueprint as a structured JSON for external use."""
    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project.id)
    )
    blueprint = result.scalars().first()
    if not blueprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    return {
        "company_name": blueprint.company_name,
        "industry": blueprint.industry,
        "business_model": blueprint.business_model,
        "target_audience": blueprint.target_audience,
        "value_proposition": blueprint.value_proposition,
        "products_services": blueprint.products_services or [],
        "competitors": blueprint.competitors or [],
        "revenue_model": blueprint.revenue_model,
        "pricing": blueprint.pricing or {},
        "team_size": blueprint.team_size,
        "budget": blueprint.budget,
        "geography": blueprint.geography,
        "tech_stack": blueprint.tech_stack,
        "marketing_strategy": blueprint.marketing_strategy,
        "sales_strategy": blueprint.sales_strategy,
        "current_goals": blueprint.current_goals or [],
        "current_problems": blueprint.current_problems or [],
        "product_roadmap": blueprint.product_roadmap or [],
        "brand_voice": blueprint.brand_voice,
        "growth_stage": blueprint.growth_stage,
        "discovery_confidence": blueprint.discovery_confidence,
        "field_confidences": blueprint.field_confidences or {},
        "version": blueprint.version,
        "last_updated": blueprint.last_updated.isoformat() if blueprint.last_updated else None,
    }
