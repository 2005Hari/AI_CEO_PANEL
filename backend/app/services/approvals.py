"""Lightweight approval workflow helpers."""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Approval, Task, Deliverable
from app.services.decisions import log_decision


async def request_approval(
    db: AsyncSession,
    *,
    project_id: str,
    resource_type: str,
    resource_id: str,
    requested_by: Optional[str] = None,
    reason: Optional[str] = None,
) -> Approval:
    approval = Approval(
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        requested_by=requested_by,
        requested_at=datetime.utcnow(),
        status="pending",
        history=[{"action": "requested", "by": requested_by, "reason": reason, "at": datetime.utcnow().isoformat()}],
    )
    db.add(approval)

    # If resource is a task, mark task approval_status pending and record review_requested_at
    if resource_type == "task":
        q = await db.execute(select(Task).where(Task.id == resource_id))
        task = q.scalars().first()
        if task:
            task.approval_status = "pending"
            task.review_requested_at = datetime.utcnow()
            task.approval_history = (task.approval_history or []) + [
                {"event": "approval_requested", "by": requested_by, "reason": reason, "at": datetime.utcnow().isoformat()}
            ]
            db.add(task)

    await db.commit()
    await db.refresh(approval)

    # Log decision-like event
    await log_decision(
        db,
        project_id=project_id,
        decision_type="approval_requested",
        source="system",
        summary=f"Approval requested for {resource_type} {resource_id}",
        context={"approval_id": approval.id, "reason": reason},
        publish=False,
    )

    return approval


async def decide_approval(
    db: AsyncSession,
    *,
    approval_id: str,
    approver_id: str,
    approve: bool,
    reason: Optional[str] = None,
) -> Approval:
    q = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = q.scalars().first()
    if not approval:
        raise ValueError("Approval not found")

    approval.status = "approved" if approve else "rejected"
    approval.approver_id = approver_id
    approval.decided_at = datetime.utcnow()
    entry = {"action": "approved" if approve else "rejected", "by": approver_id, "reason": reason, "at": datetime.utcnow().isoformat()}
    approval.history = (approval.history or []) + [entry]
    db.add(approval)

    # Update underlying resource status
    if approval.resource_type == "task":
        q = await db.execute(select(Task).where(Task.id == approval.resource_id))
        task = q.scalars().first()
        if task:
            task.approval_status = approval.status
            if approve:
                task.stage = "done"
                task.completed_at = datetime.utcnow()
            task.approval_history = (task.approval_history or []) + [entry]
            db.add(task)
    elif approval.resource_type == "deliverable":
        q = await db.execute(select(Deliverable).where(Deliverable.id == approval.resource_id))
        d = q.scalars().first()
        if d:
            d.status = approval.status
            if approve:
                d.approved_at = datetime.utcnow()
                d.approved_by_user_id = approver_id
            db.add(d)

    await db.commit()
    await db.refresh(approval)

    # Record a decision log
    await log_decision(
        db,
        project_id=approval.project_id,
        decision_type="approval_decision",
        source="user",
        summary=f"Approval {approval.status} by {approver_id}",
        context={"approval_id": approval.id, "reason": reason},
        source_agent=None,
        publish=False,
    )

    return approval


async def get_approval(db: AsyncSession, approval_id: str) -> Optional[Approval]:
    q = await db.execute(select(Approval).where(Approval.id == approval_id))
    return q.scalars().first()


async def list_pending_approvals_for_project(db: AsyncSession, project_id: str):
    q = await db.execute(select(Approval).where(Approval.project_id == project_id).where(Approval.status == "pending"))
    return q.scalars().all()
