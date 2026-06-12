from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project
from app.services.approvals import request_approval, decide_approval, list_pending_approvals_for_project

router = APIRouter()

class ApprovalRequest(BaseModel):
    resource_type: str
    resource_id: str
    reason: Optional[str] = None

class ApprovalDecision(BaseModel):
    approve: bool
    reason: Optional[str] = None


@router.post("/projects/{project_id}/approvals/request")
async def api_request_approval(
    req: ApprovalRequest,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    approval = await request_approval(db, project_id=project.id, resource_type=req.resource_type, resource_id=req.resource_id, requested_by=None, reason=req.reason)
    return {"status": "ok", "approval_id": approval.id}


@router.post("/projects/{project_id}/approvals/{approval_id}/decide")
async def api_decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        approval = await decide_approval(db, approval_id=approval_id, approver_id=None, approve=decision.approve, reason=decision.reason)
        return {"status": "ok", "approval_id": approval.id, "result": approval.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/approvals/pending")
async def api_list_pending(project: Project = Depends(get_project_for_user), db: AsyncSession = Depends(get_db)):
    items = await list_pending_approvals_for_project(db, project.id)
    return {"count": len(items), "approvals": [ {"id": a.id, "resource_type": a.resource_type, "resource_id": a.resource_id, "requested_at": a.requested_at} for a in items ]}
