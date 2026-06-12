"""Sync CompanyBlueprint → CompanyOperatingProfile (backward compatible)."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import CompanyBlueprint, CompanyOperatingProfile, Project


BLUEPRINT_TO_PROFILE_FIELDS = [
    "company_name",
    "industry",
    "business_model",
    "target_audience",
    "value_proposition",
    "products_services",
    "competitors",
    "revenue_model",
    "pricing",
    "team_size",
    "budget",
    "geography",
    "tech_stack",
    "marketing_strategy",
    "sales_strategy",
    "current_goals",
    "current_problems",
    "product_roadmap",
    "brand_voice",
    "growth_stage",
]


def _team_structure_from_blueprint(blueprint: CompanyBlueprint) -> Dict[str, Any]:
    if blueprint.team_size:
        return {"summary": blueprint.team_size, "roles": []}
    return {}


async def get_or_create_operating_profile(
    db: AsyncSession, project_id: str
) -> CompanyOperatingProfile:
    result = await db.execute(
        select(CompanyOperatingProfile).where(CompanyOperatingProfile.project_id == project_id)
    )
    profile = result.scalars().first()
    if profile:
        return profile

    profile = CompanyOperatingProfile(project_id=project_id)
    db.add(profile)
    await db.flush()
    return profile


async def sync_operating_profile_from_blueprint(
    db: AsyncSession,
    project_id: str,
    *,
    preserve_extensions: bool = True,
) -> Tuple[CompanyOperatingProfile, List[str]]:
    """
    Mirror blueprint fields into the operating profile.
    Preserves profile-only fields (customer_segments, risks, assets) when preserve_extensions=True.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()

    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project_id)
    )
    blueprint = result.scalars().first()

    profile = await get_or_create_operating_profile(db, project_id)
    updated_fields: List[str] = []

    if blueprint:
        for field in BLUEPRINT_TO_PROFILE_FIELDS:
            value = getattr(blueprint, field, None)
            if value is not None:
                setattr(profile, field, value)
                updated_fields.append(field)
                if isinstance(value, (list, dict)):
                    flag_modified(profile, field)

        profile.discovery_confidence = blueprint.discovery_confidence or 0.0
        profile.synced_from_blueprint_version = blueprint.version or 1
        if not preserve_extensions or not profile.team_structure:
            profile.team_structure = _team_structure_from_blueprint(blueprint)
            updated_fields.append("team_structure")

    if project:
        profile.operating_mode = project.operating_mode or "startup"
        if not profile.company_name and project.name:
            profile.company_name = project.name
            updated_fields.append("company_name")

    profile.last_synced_at = datetime.utcnow()
    profile.version = (profile.version or 1) + (1 if updated_fields else 0)
    profile.last_updated = datetime.utcnow()

    await db.commit()
    await db.refresh(profile)
    return profile, updated_fields


def operating_profile_to_dict(profile: CompanyOperatingProfile) -> Dict[str, Any]:
    return {
        "id": profile.id,
        "project_id": profile.project_id,
        "company_name": profile.company_name,
        "industry": profile.industry,
        "business_model": profile.business_model,
        "target_audience": profile.target_audience,
        "value_proposition": profile.value_proposition,
        "market_positioning": profile.market_positioning,
        "products_services": profile.products_services or [],
        "competitors": profile.competitors or [],
        "customer_segments": profile.customer_segments or [],
        "revenue_model": profile.revenue_model,
        "pricing": profile.pricing or {},
        "team_structure": profile.team_structure or {},
        "team_size": profile.team_size,
        "budget": profile.budget,
        "geography": profile.geography,
        "tech_stack": profile.tech_stack,
        "marketing_strategy": profile.marketing_strategy,
        "sales_strategy": profile.sales_strategy,
        "marketing_assets": profile.marketing_assets or [],
        "technical_assets": profile.technical_assets or [],
        "current_goals": profile.current_goals or [],
        "current_problems": profile.current_problems or [],
        "product_roadmap": profile.product_roadmap or [],
        "risks": profile.risks or [],
        "brand_voice": profile.brand_voice,
        "growth_stage": profile.growth_stage,
        "operating_mode": profile.operating_mode,
        "discovery_confidence": profile.discovery_confidence,
        "version": profile.version,
        "last_synced_at": profile.last_synced_at.isoformat() if profile.last_synced_at else None,
        "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
    }
