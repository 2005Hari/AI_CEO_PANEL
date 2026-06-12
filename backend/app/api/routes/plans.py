from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, Plan

router = APIRouter()


@router.get("/projects/{project_id}/plans")
async def list_plans(project: Project = Depends(get_project_for_user), db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Plan).where(Plan.project_id == project.id))
    plans = q.scalars().all()
    return {
        "plans": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "status": p.status,
                "owner_agent": p.owner_agent,
                "milestones": p.milestones,
                "confidence_score": p.confidence_score,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in plans
        ]
    }


@router.get("/projects/{project_id}/plans/{plan_id}")
async def get_plan(plan_id: str, project: Project = Depends(get_project_for_user), db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Plan).where(Plan.id == plan_id).where(Plan.project_id == project.id))
    plan = q.scalars().first()
    if not plan:
        return {"error": "Plan not found"}
    return {
        "id": plan.id,
        "title": plan.title,
        "description": plan.description,
        "status": plan.status,
        "owner_agent": plan.owner_agent,
        "milestones": plan.milestones,
        "confidence_score": plan.confidence_score,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }
