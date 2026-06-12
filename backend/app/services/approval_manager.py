from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Approval, Task

class ApprovalManager:
    @staticmethod
    async def request_approval(db: AsyncSession, project_id: str, resource_type: str, resource_id: str, requested_by: str) -> Approval:
        approval = Approval(
            project_id=project_id,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_by=requested_by,
            status="pending"
        )
        db.add(approval)
        
        # If it's a task, update its approval status
        if resource_type == "task":
            from sqlalchemy import select
            result = await db.execute(select(Task).where(Task.id == resource_id))
            task = result.scalars().first()
            if task:
                task.approval_status = "pending"
                
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def approve(db: AsyncSession, approval_id: str, approver_id: str):
        from sqlalchemy import select
        result = await db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalars().first()
        if not approval:
            return None
            
        approval.status = "approved"
        approval.approver_id = approver_id
        
        if approval.resource_type == "task":
            result = await db.execute(select(Task).where(Task.id == approval.resource_id))
            task = result.scalars().first()
            if task:
                task.approval_status = "approved"
                
        await db.commit()
        return approval
