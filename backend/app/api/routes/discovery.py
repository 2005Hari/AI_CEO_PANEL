# backend/app/api/routes/discovery.py
"""Discovery interview endpoints — interactive founder Q&A to build the CompanyBlueprint."""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, CompanyBlueprint
from app.orchestrator.discovery import (
    calculate_confidence,
    get_missing_fields,
    generate_discovery_questions,
    process_discovery_response,
    FIELD_QUESTIONS,
)

router = APIRouter()


class DiscoveryStartResponse(BaseModel):
    status: str
    confidence: float
    missing_fields: List[str]
    questions: str

class DiscoveryRespondRequest(BaseModel):
    response: str
    conversation_history: List[Dict[str, str]] = []

class DiscoveryRespondResponse(BaseModel):
    status: str
    confidence: float
    updated_fields: List[str] = []
    message: str
    next_questions: str

class DiscoveryStatusResponse(BaseModel):
    confidence: float
    missing_fields: List[str]
    total_fields: int
    filled_fields: int
    is_complete: bool


@router.post("/projects/{project_id}/discovery/start", response_model=DiscoveryStartResponse)
async def start_discovery(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Initialize or resume the discovery interview."""
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

    confidence = calculate_confidence(blueprint)
    missing = get_missing_fields(blueprint)

    if confidence >= 0.9:
        return DiscoveryStartResponse(
            status="complete",
            confidence=confidence,
            missing_fields=missing,
            questions="Your Company Blueprint is already comprehensive! You can update it anytime from Settings."
        )

    questions = await generate_discovery_questions(blueprint, [])
    return DiscoveryStartResponse(
        status="in_progress",
        confidence=confidence,
        missing_fields=missing,
        questions=questions
    )


@router.post("/projects/{project_id}/discovery/respond", response_model=DiscoveryRespondResponse)
async def respond_to_discovery(
    req: DiscoveryRespondRequest,
    project: Project = Depends(get_project_for_user),
):
    """Process founder's response and extract structured data into the blueprint."""
    result = await process_discovery_response(
        project_id=project.id,
        founder_response=req.response,
        conversation_history=req.conversation_history
    )
    return DiscoveryRespondResponse(**result)


@router.get("/projects/{project_id}/discovery/status", response_model=DiscoveryStatusResponse)
async def discovery_status(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Check current discovery completion status."""
    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project.id)
    )
    blueprint = result.scalars().first()

    if not blueprint:
        return DiscoveryStatusResponse(
            confidence=0.0,
            missing_fields=list(FIELD_QUESTIONS.keys()),
            total_fields=len(FIELD_QUESTIONS),
            filled_fields=0,
            is_complete=False
        )

    confidence = calculate_confidence(blueprint)
    missing = get_missing_fields(blueprint)

    return DiscoveryStatusResponse(
        confidence=confidence,
        missing_fields=missing,
        total_fields=len(FIELD_QUESTIONS),
        filled_fields=len(FIELD_QUESTIONS) - len(missing),
        is_complete=confidence >= 0.9
    )


@router.post("/projects/{project_id}/discovery/finalize")
async def finalize_discovery(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark discovery as complete and lock the blueprint."""
    result = await db.execute(
        select(CompanyBlueprint).where(CompanyBlueprint.project_id == project.id)
    )
    blueprint = result.scalars().first()
    if not blueprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No blueprint found. Start discovery first.")

    confidence = calculate_confidence(blueprint)
    blueprint.discovery_confidence = confidence
    project.discovery_completed = True

    await db.commit()

    return {
        "status": "finalized",
        "confidence": confidence,
        "message": "Company Blueprint has been finalized. Your AI team now has full context."
    }
