# backend/app/api/routes/activity.py
"""Activity feed endpoints (HTTP and WebSocket) for real-time agent activity tracking."""
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps.auth import get_current_user, get_current_user_from_token
from app.api.deps.project import get_project_for_user
from app.db.models import AgentActivity, Project, User
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()


class ActivityResponse(BaseModel):
    id: str
    project_id: str
    task_id: Optional[str] = None
    agent_role: str
    activity_type: str
    message: Optional[str] = None
    metadata_json: dict = {}
    created_at: str

    class Config:
        from_attributes = True


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.get("/projects/{project_id}/activity", response_model=List[ActivityResponse])
async def get_activity_feed(
    limit: int = 50,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the recent activity feed for a project."""
    query = (
        select(AgentActivity)
        .where(AgentActivity.project_id == project.id)
        .order_by(AgentActivity.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    activities = result.scalars().all()

    return [
        ActivityResponse(
            id=activity.id,
            project_id=activity.project_id,
            task_id=activity.task_id,
            agent_role=activity.agent_role,
            activity_type=activity.activity_type,
            message=activity.message,
            metadata_json=activity.metadata_json or {},
            created_at=activity.created_at.isoformat(),
        )
        for activity in activities
    ]


@router.websocket("/projects/{project_id}/activity/live")
async def activity_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    """Real-time WebSocket endpoint for the activity feed."""
    async with AsyncSessionLocal() as db:
        try:
            user = await get_current_user_from_token(token, db)
            result = await db.execute(
                select(Project).where(Project.id == project_id, Project.user_id == user.id)
            )
            if not result.scalars().first():
                await websocket.close(code=4403)
                return
        except HTTPException:
            await websocket.close(code=4401)
            return

    await manager.connect(websocket, project_id)

    try:
        while True:
            # Events are pushed instantly via manager.broadcast() from
            # activity_logger.log_activity(). We just need to keep the
            # connection open and detect client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
