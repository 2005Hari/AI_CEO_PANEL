from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.auth import get_current_user
from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, User, Workspace

router = APIRouter()


class ProjectBase(BaseModel):
    name: str
    core_context: Dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    workspace_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    core_context: Dict[str, Any]


class ProjectResponse(BaseModel):
    id: str
    name: str
    core_context: Dict[str, Any]
    operating_mode: str = "startup"
    discovery_completed: bool = False
    health_score: Optional[float] = None
    workspace_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


async def _ensure_default_workspace(db: AsyncSession, user: User) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.user_id == user.id).limit(1))
    workspace = result.scalars().first()
    if workspace:
        return workspace
    workspace = Workspace(user_id=user.id, name="My Workspace")
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace_id = project_in.workspace_id
    if workspace_id:
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == current_user.id)
        )
        if not result.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    else:
        workspace = await _ensure_default_workspace(db, current_user)
        workspace_id = workspace.id

    core_ctx = {
        "company_name": project_in.name,
        "value_proposition": "",
        "target_audience": "",
        "tech_stack": "",
        "business_model": "",
        **project_in.core_context,
    }

    db_project = Project(
        name=project_in.name,
        user_id=current_user.id,
        workspace_id=workspace_id,
        core_context=core_ctx,
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project: Project = Depends(get_project_for_user)):
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_in: ProjectUpdate,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    if project_in.name is not None:
        project.name = project_in.name

    updated_context = {**(project.core_context or {})}
    updated_context.update(project_in.core_context)

    from sqlalchemy.orm.attributes import flag_modified
    project.core_context = updated_context
    flag_modified(project, "core_context")

    await db.commit()
    await db.refresh(project)
    return project
