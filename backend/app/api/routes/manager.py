# backend/app/api/routes/manager.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any, List

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project
from app.orchestrator.manager import decompose_and_delegate
from app.orchestrator.manager_v2 import create_plan_and_tasks

router = APIRouter()

class ManagerPlanRequest(BaseModel):
    request: str

class ManagerPlanResponse(BaseModel):
    status: str
    plan_summary: str = ""
    tasks_created: List[Dict[str, Any]] = []
    message: str = ""

@router.post("/projects/{project_id}/manager/plan", response_model=ManagerPlanResponse)
async def manager_plan(
    req: ManagerPlanRequest,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a complex request to the Manager Agent.
    The Manager will break it down into actionable tasks and assign them to specialized agents.
    """
    result_data = await decompose_and_delegate(project.id, req.request, db)
    
    if result_data["status"] == "error":
        raise HTTPException(status_code=500, detail=result_data.get("message", "Manager failed to decompose request"))
        
    return ManagerPlanResponse(**result_data)


@router.post("/projects/{project_id}/manager/plan_v2")
async def manager_plan_v2(
    req: ManagerPlanRequest,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    result = await create_plan_and_tasks(project.id, req.request, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Manager v2 failed"))
    return result
