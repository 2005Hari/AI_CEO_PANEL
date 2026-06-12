# backend/app/api/routes/tasks.py
"""Task engine CRUD + execution endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user, get_task_for_user
from app.db.session import get_db
from app.db.models import Task, Project, AgentActivity

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: str = "medium"
    parent_task_id: Optional[str] = None
    input_context: dict = {}

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[float] = None

class TaskResponse(BaseModel):
    id: str
    project_id: str
    parent_task_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    status: str
    priority: str
    progress: float
    input_context: dict = {}
    output_result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status_filter: Optional[str] = None,
    agent_filter: Optional[str] = None,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tasks for a project with optional filtering."""
    query = select(Task).where(Task.project_id == project.id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if agent_filter:
        query = query.where(Task.assigned_agent == agent_filter)
    query = query.order_by(Task.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    task = Task(
        project_id=project.id,
        title=task_in.title,
        description=task_in.description,
        assigned_agent=task_in.assigned_agent,
        priority=task_in.priority,
        parent_task_id=task_in.parent_task_id,
        input_context=task_in.input_context,
        status="assigned" if task_in.assigned_agent else "pending"
    )
    db.add(task)

    # Log activity
    if task_in.assigned_agent:
        activity = AgentActivity(
            project_id=project.id,
            agent_role=task_in.assigned_agent,
            activity_type="assigned",
            message=f"Task assigned: {task_in.title}"
        )
        db.add(activity)

    await db.commit()
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task: Task = Depends(get_task_for_user)):
    """Get a specific task with its output."""
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_in: TaskUpdate,
    task: Task = Depends(get_task_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task's fields."""

    update_data = task_in.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Track status transitions
    if "status" in update_data:
        if update_data["status"] == "working" and not task.started_at:
            task.started_at = datetime.utcnow()
        elif update_data["status"] == "completed":
            task.completed_at = datetime.utcnow()
            task.progress = 1.0

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task: Task = Depends(get_task_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger agent execution for a task. Runs the assigned agent with task context."""
    if not task.assigned_agent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No agent assigned to this task")

    # Update status
    task.status = "working"
    task.started_at = datetime.utcnow()
    
    # Log activity
    activity = AgentActivity(
        project_id=task.project_id,
        task_id=task.id,
        agent_role=task.assigned_agent,
        activity_type="generating",
        message=f"Working on: {task.title}"
    )
    db.add(activity)
    await db.commit()

    # Execute via the agent system
    try:
        from app.services.task_engine import execute_agent_task
        result_data = await execute_agent_task(task)
        
        task.output_result = result_data
        task.status = "review"
        task.progress = 0.9
        
        # Log completion
        completion_activity = AgentActivity(
            project_id=task.project_id,
            task_id=task.id,
            agent_role=task.assigned_agent,
            activity_type="completed",
            message=f"Completed: {task.title}"
        )
        db.add(completion_activity)
        
    except Exception as e:
        task.status = "blocked"
        task.error_message = str(e)
        
        error_activity = AgentActivity(
            project_id=task.project_id,
            task_id=task.id,
            agent_role=task.assigned_agent,
            activity_type="error",
            message=f"Failed: {str(e)}"
        )
        db.add(error_activity)

    await db.commit()
    await db.refresh(task)

    if task.status in ("review", "completed"):
        from app.services.decisions import log_decision
        from app.services.memory_hooks import on_task_completed

        await log_decision(
            db,
            project_id=task.project_id,
            decision_type="operational",
            source="agent",
            source_agent=task.assigned_agent,
            summary=f"Task completed: {task.title}",
            context={"task_id": task.id, "status": task.status},
            related_task_id=task.id,
            publish=True,
        )
        await on_task_completed(task.project_id, task.id, task.assigned_agent)

    return TaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task: Task = Depends(get_task_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel and delete a task."""
    await db.delete(task)
    await db.commit()


@router.get("/projects/{project_id}/tasks/stats")
async def task_stats(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task statistics for the project dashboard."""
    result = await db.execute(select(Task).where(Task.project_id == project.id))
    tasks = result.scalars().all()
    
    stats = {"pending": 0, "assigned": 0, "working": 0, "review": 0, "completed": 0, "blocked": 0, "total": len(tasks)}
    for t in tasks:
        stats[t.status] = stats.get(t.status, 0) + 1
    
    return stats
