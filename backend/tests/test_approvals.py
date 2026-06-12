"""Tests for approval workflow."""
import pytest
from datetime import datetime
import pytest_asyncio
from sqlalchemy import select

from app.db.models import Approval, Task, Deliverable, Plan
from app.db.session import AsyncSessionLocal
from app.services.approvals import request_approval, decide_approval, get_approval, list_pending_approvals_for_project


@pytest_asyncio.fixture
async def project_with_plan_and_tasks(user_project):
    """Create a project with a plan and tasks."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Test Plan",
            description="Test plan for approvals",
            status="active",
            owner_agent="manager",
            generated_by="manager_v2"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        task1 = Task(
            project_id=user_project.id,
            plan_id=plan.id,
            title="Design landing page",
            description="Create Figma mockup",
            assigned_agent="designer",
            priority="high",
            status="assigned",
            review_required=True,
            input_context={}
        )
        db.add(task1)
        await db.commit()
        await db.refresh(task1)

        task2 = Task(
            project_id=user_project.id,
            plan_id=plan.id,
            title="Implement frontend",
            description="Code the landing page",
            assigned_agent="developer",
            priority="high",
            status="in_progress",
            review_required=True,
            input_context={}
        )
        db.add(task2)
        await db.commit()
        await db.refresh(task2)

        deliverable = Deliverable(
            project_id=user_project.id,
            plan_id=plan.id,
            task_id=task1.id,
            deliverable_type="frontend",
            title="Landing Page",
            status="pending",
            content_markdown="# Landing Page\nMockup content",
            created_by_agent="designer"
        )
        db.add(deliverable)
        await db.commit()
        await db.refresh(deliverable)

    return {
        "project": user_project,
        "plan": plan,
        "task1": task1,
        "task2": task2,
        "deliverable": deliverable
    }


@pytest.mark.asyncio
async def test_request_approval_for_task(project_with_plan_and_tasks):
    """Test requesting approval for a task."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="founder@example.com",
            reason="Ready for review"
        )

    assert approval.status == "pending"
    assert approval.resource_type == "task"
    assert approval.requested_by == "founder@example.com"
    assert approval.requested_at is not None

    # Verify task is marked for approval
    async with AsyncSessionLocal() as db:
        task_q = await db.execute(select(Task).where(Task.id == project_with_plan_and_tasks["task1"].id))
        task = task_q.scalars().first()
        assert task.approval_status == "pending"
        assert task.review_requested_at is not None


@pytest.mark.asyncio
async def test_request_approval_for_deliverable(project_with_plan_and_tasks):
    """Test requesting approval for a deliverable."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="deliverable",
            resource_id=project_with_plan_and_tasks["deliverable"].id,
            requested_by="developer@example.com",
            reason="Landing page design complete"
        )

    assert approval.status == "pending"
    assert approval.resource_type == "deliverable"
    assert approval.history[0]["action"] == "requested"


@pytest.mark.asyncio
async def test_decide_approval_approve(project_with_plan_and_tasks):
    """Test approving an approval request."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="developer@example.com"
        )

        approval_id = approval.id

    async with AsyncSessionLocal() as db:
        approval = await decide_approval(
            db,
            approval_id=approval_id,
            approver_id="founder@example.com",
            approve=True,
            reason="Looks good!"
        )

    assert approval.status == "approved"
    assert approval.approver_id == "founder@example.com"
    assert approval.decided_at is not None
    assert len(approval.history) == 2
    assert approval.history[1]["action"] == "approved"

    # Verify task is marked as approved
    async with AsyncSessionLocal() as db:
        task_q = await db.execute(select(Task).where(Task.id == project_with_plan_and_tasks["task1"].id))
        task = task_q.scalars().first()
        assert task.approval_status == "approved"
        assert task.stage == "done"
        assert task.completed_at is not None


@pytest.mark.asyncio
async def test_decide_approval_reject(project_with_plan_and_tasks):
    """Test rejecting an approval request."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="developer@example.com"
        )

        approval_id = approval.id

    async with AsyncSessionLocal() as db:
        approval = await decide_approval(
            db,
            approval_id=approval_id,
            approver_id="founder@example.com",
            approve=False,
            reason="Needs revision"
        )

    assert approval.status == "rejected"
    assert approval.approver_id == "founder@example.com"
    assert approval.history[1]["reason"] == "Needs revision"

    # Verify task is marked as rejected (but not done)
    async with AsyncSessionLocal() as db:
        task_q = await db.execute(select(Task).where(Task.id == project_with_plan_and_tasks["task1"].id))
        task = task_q.scalars().first()
        assert task.approval_status == "rejected"
        assert task.stage != "done"  # Stage should not change to done


@pytest.mark.asyncio
async def test_decide_approval_deliverable(project_with_plan_and_tasks):
    """Test approving a deliverable."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="deliverable",
            resource_id=project_with_plan_and_tasks["deliverable"].id,
            requested_by="developer@example.com"
        )

        approval_id = approval.id

    async with AsyncSessionLocal() as db:
        approval = await decide_approval(
            db,
            approval_id=approval_id,
            approver_id="founder@example.com",
            approve=True,
            reason="Perfect!"
        )

    assert approval.status == "approved"

    # Verify deliverable is marked as approved
    async with AsyncSessionLocal() as db:
        dv_q = await db.execute(select(Deliverable).where(Deliverable.id == project_with_plan_and_tasks["deliverable"].id))
        dv = dv_q.scalars().first()
        assert dv.approval_status == "approved"
        assert dv.approved_at is not None
        assert dv.approved_by_user_id == "founder@example.com"


@pytest.mark.asyncio
async def test_get_approval(project_with_plan_and_tasks):
    """Test fetching a single approval."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="developer@example.com"
        )

        approval_id = approval.id

    async with AsyncSessionLocal() as db:
        approval = await get_approval(db, approval_id)

    assert approval is not None
    assert approval.id == approval_id
    assert approval.status == "pending"


@pytest.mark.asyncio
async def test_list_pending_approvals(project_with_plan_and_tasks):
    """Test listing pending approvals for a project."""
    async with AsyncSessionLocal() as db:
        # Create multiple approvals
        approval1 = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="dev@example.com"
        )

        approval2 = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task2"].id,
            requested_by="dev@example.com"
        )

    async with AsyncSessionLocal() as db:
        pending = await list_pending_approvals_for_project(
            db,
            project_with_plan_and_tasks["project"].id
        )

    assert len(pending) == 2
    assert all(a.status == "pending" for a in pending)


@pytest.mark.asyncio
async def test_list_pending_approvals_excludes_decided(project_with_plan_and_tasks):
    """Test that decided approvals are not in pending list."""
    async with AsyncSessionLocal() as db:
        approval1 = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="dev@example.com"
        )

        approval2 = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task2"].id,
            requested_by="dev@example.com"
        )

        # Approve the first one
        await decide_approval(
            db,
            approval_id=approval1.id,
            approver_id="founder@example.com",
            approve=True
        )

    async with AsyncSessionLocal() as db:
        pending = await list_pending_approvals_for_project(
            db,
            project_with_plan_and_tasks["project"].id
        )

    assert len(pending) == 1
    assert pending[0].id == approval2.id


@pytest.mark.asyncio
async def test_approval_history_tracked(project_with_plan_and_tasks):
    """Test that approval history is maintained."""
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=project_with_plan_and_tasks["project"].id,
            resource_type="task",
            resource_id=project_with_plan_and_tasks["task1"].id,
            requested_by="dev@example.com",
            reason="Ready for review"
        )

        assert len(approval.history) == 1
        assert approval.history[0]["action"] == "requested"

        await decide_approval(
            db,
            approval_id=approval.id,
            approver_id="founder@example.com",
            approve=True,
            reason="Looks good"
        )

    async with AsyncSessionLocal() as db:
        approval = await get_approval(db, approval.id)
        assert len(approval.history) == 2
        assert approval.history[0]["action"] == "requested"
        assert approval.history[1]["action"] == "approved"


@pytest.mark.asyncio
async def test_approval_project_isolation(user_project, second_user):
    """Test that approvals are isolated by project."""
    # Create another project for second user
    async with AsyncSessionLocal() as db:
        other_project = await db.execute(select(Project).where(Project.user_id == second_user.id))
        other_proj = other_project.scalars().first()
        if not other_proj:
            from app.db.models import Project
            other_proj = Project(name="Other Startup", user_id=second_user.id, core_context={})
            db.add(other_proj)
            await db.commit()
            await db.refresh(other_proj)

    # Create tasks in both projects
    async with AsyncSessionLocal() as db:
        task1 = Task(
            project_id=user_project.id,
            title="Task in project 1",
            assigned_agent="developer",
            status="assigned",
            input_context={}
        )
        db.add(task1)
        await db.commit()
        await db.refresh(task1)

    # Request approval in project 1
    async with AsyncSessionLocal() as db:
        approval = await request_approval(
            db,
            project_id=user_project.id,
            resource_type="task",
            resource_id=task1.id,
            requested_by="founder@example.com"
        )

    # Check that only project 1's approval is listed
    async with AsyncSessionLocal() as db:
        project1_pending = await list_pending_approvals_for_project(db, user_project.id)
        project2_pending = await list_pending_approvals_for_project(db, other_proj.id)

    assert len(project1_pending) == 1
    assert len(project2_pending) == 0


# Import required fixtures
import pytest_asyncio
from app.db.models import Project
