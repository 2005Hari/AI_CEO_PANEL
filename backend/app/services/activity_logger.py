# backend/app/services/activity_logger.py
"""
Central helper for emitting 'live agent activity' events.

Every call:
 1. Persists an AgentActivity row (so the HTTP /activity feed and page
    reloads still show full history)
 2. Immediately broadcasts the event over the project's websocket so the
    frontend can render it in real time (no polling delay)

Usage:
    from app.services.activity_logger import log_activity

    await log_activity(
        project_id=task.project_id,
        agent_role="developer",
        activity_type="thinking",
        message="Reading company blueprint and task requirements...",
        task_id=task.id,
    )
"""
from datetime import datetime
from typing import Optional, Any, Dict

from app.db.session import AsyncSessionLocal
from app.db.models import AgentActivity


async def log_activity(
    project_id: str,
    agent_role: str,
    activity_type: str,
    message: Optional[str] = None,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentActivity:
    """Persist an activity row and broadcast it live to connected clients."""
    metadata = metadata or {}

    async with AsyncSessionLocal() as db:
        activity = AgentActivity(
            project_id=project_id,
            task_id=task_id,
            agent_role=agent_role,
            activity_type=activity_type,
            message=message,
            metadata_json=metadata,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(activity)

    # Broadcast live (import here to avoid circular imports at module load time)
    try:
        from app.api.routes.activity import manager as activity_ws_manager

        await activity_ws_manager.broadcast(
            project_id,
            {
                "type": "new_activity",
                "data": {
                    "id": activity.id,
                    "task_id": activity.task_id,
                    "agent_role": activity.agent_role,
                    "activity_type": activity.activity_type,
                    "message": activity.message,
                    "metadata": activity.metadata_json or {},
                    "created_at": activity.created_at.isoformat(),
                },
            },
        )
    except Exception as e:
        # Never let a broadcast failure break task execution
        print(f"[activity_logger] broadcast failed: {e}")

    return activity
