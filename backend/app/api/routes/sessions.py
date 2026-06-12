from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user, get_session_for_user
from app.db.session import get_db
from app.db.models import Session, Message, Project

router = APIRouter()


class SessionResponse(BaseModel):
    id: str
    project_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    agent_drafts: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/sessions", response_model=List[SessionResponse])
async def list_sessions(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.project_id == project.id)
        .order_by(Session.created_at.desc())
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    session: Session = Depends(get_session_for_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    session = Session(project_id=project.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
