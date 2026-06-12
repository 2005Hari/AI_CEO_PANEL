from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.project import get_project_for_user
from app.db.models import DecisionLog, Project
from app.db.session import get_db

router = APIRouter()


class DecisionResponse(BaseModel):
    id: str
    project_id: str
    decision_type: str
    source: str
    source_agent: Optional[str] = None
    summary: str
    context: Dict[str, Any] = {}
    related_task_id: Optional[str] = None
    related_session_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/decisions", response_model=List[DecisionResponse])
async def list_decisions(
    limit: int = 50,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DecisionLog)
        .where(DecisionLog.project_id == project.id)
        .order_by(DecisionLog.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
