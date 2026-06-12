from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, Task, Deliverable, Approval

router = APIRouter()

@router.get("/projects/{project_id}/metrics")
async def project_metrics(project: Project = Depends(get_project_for_user), db: AsyncSession = Depends(get_db)):
    # Tasks by status
    q = await db.execute(select(Task.status, func.count(Task.id)).where(Task.project_id == project.id).group_by(Task.status))
    tasks_status = {row[0]: row[1] for row in q.all()}

    q = await db.execute(select(Deliverable.status, func.count(Deliverable.id)).where(Deliverable.project_id == project.id).group_by(Deliverable.status))
    deliverables_status = {row[0]: row[1] for row in q.all()}

    q = await db.execute(select(Approval.status, func.count(Approval.id)).where(Approval.project_id == project.id).group_by(Approval.status))
    approvals_status = {row[0]: row[1] for row in q.all()}

    # Calculate Company Health Score based on task completion
    completed_tasks = tasks_status.get("completed", 0)
    total_tasks = sum(tasks_status.values())
    health_score = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    return {
        "tasks": tasks_status,
        "deliverables": deliverables_status,
        "approvals": approvals_status,
        "company_health_score": health_score,
    }
