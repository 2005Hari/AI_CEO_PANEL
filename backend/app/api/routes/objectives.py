# backend/app/api/routes/objectives.py
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user, get_objective_for_user
from app.db.session import get_db
from app.db.models import Project, Objective

router = APIRouter()

class ObjectiveCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[datetime] = None

class ObjectiveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    target_date: Optional[datetime] = None

class ObjectiveResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    progress: float
    target_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/projects/{project_id}/objectives", response_model=List[ObjectiveResponse])
async def list_objectives(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """List all objectives for a project."""
    query = select(Objective).where(Objective.project_id == project.id).order_by(Objective.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/projects/{project_id}/objectives", response_model=ObjectiveResponse, status_code=status.HTTP_201_CREATED)
async def create_objective(
    obj_in: ObjectiveCreate,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new objective."""
    obj = Objective(
        project_id=project.id,
        title=obj_in.title,
        description=obj_in.description,
        category=obj_in.category,
        target_date=obj_in.target_date
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    from app.services.memory_hooks import on_objective_changed
    await on_objective_changed(project.id, obj.id, "created", obj.title)
    return obj

@router.put("/objectives/{obj_id}", response_model=ObjectiveResponse)
async def update_objective(
    obj_in: ObjectiveUpdate,
    obj: Objective = Depends(get_objective_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an objective."""

    update_data = obj_in.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(obj, field, value)

    await db.commit()
    await db.refresh(obj)

    from app.services.memory_hooks import on_objective_changed
    await on_objective_changed(obj.project_id, obj.id, "updated", obj.title)
    return obj

@router.delete("/objectives/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_objective(
    obj: Objective = Depends(get_objective_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an objective."""
    await db.delete(obj)
    await db.commit()
