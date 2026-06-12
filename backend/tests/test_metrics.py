"""Tests for metrics aggregation and dashboard."""
import pytest
from sqlalchemy import select, func
import pytest_asyncio

from app.db.models import Task, Deliverable, Approval, Plan
from app.db.session import AsyncSessionLocal


@pytest_asyncio.fixture
async def project_with_diverse_tasks(user_project):
    """Create a project with tasks in various states."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Test Plan",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Create tasks in different statuses
        task_statuses = [
            ("task_pending_1", "pending", None),
            ("task_pending_2", "pending", None),
            ("task_assigned_1", "assigned", None),
            ("task_assigned_2", "assigned", None),
            ("task_assigned_3", "assigned", None),
            ("task_in_progress_1", "in_progress", "working"),
            ("task_in_progress_2", "in_progress", "review"),
            ("task_completed_1", "completed", None),
            ("task_blocked_1", "blocked", None),
        ]

        tasks = []
        for title, status, stage in task_statuses:
            task = Task(
                project_id=user_project.id,
                plan_id=plan.id,
                title=title,
                status=status,
                stage=stage or "todo",
                assigned_agent="developer",
                priority="medium",
                input_context={}
            )
            db.add(task)
            tasks.append(task)

        await db.commit()

    return {"project": user_project, "plan": plan}


@pytest_asyncio.fixture
async def project_with_deliverables(user_project):
    """Create a project with deliverables in various states."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Test Plan",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Create deliverables in different statuses
        deliverable_statuses = [
            ("pending_1", "pending"),
            ("pending_2", "pending"),
            ("in_progress_1", "in_progress"),
            ("in_progress_2", "in_progress"),
            ("in_progress_3", "in_progress"),
            ("ready_for_review_1", "ready_for_review"),
            ("ready_for_review_2", "ready_for_review"),
            ("approved_1", "approved"),
            ("released_1", "released"),
        ]

        deliverables = []
        for title, status in deliverable_statuses:
            dv = Deliverable(
                project_id=user_project.id,
                plan_id=plan.id,
                deliverable_type="frontend",
                title=title,
                status=status,
                created_by_agent="developer"
            )
            db.add(dv)
            deliverables.append(dv)

        await db.commit()

    return {"project": user_project, "plan": plan}


@pytest_asyncio.fixture
async def project_with_approvals(user_project):
    """Create a project with approvals in various states."""
    async with AsyncSessionLocal() as db:
        # Create tasks to approve
        task1 = Task(
            project_id=user_project.id,
            title="Task to approve",
            status="review",
            assigned_agent="developer",
            input_context={}
        )
        task2 = Task(
            project_id=user_project.id,
            title="Task to approve 2",
            status="review",
            assigned_agent="developer",
            input_context={}
        )
        db.add_all([task1, task2])
        await db.commit()
        await db.refresh(task1)
        await db.refresh(task2)

        # Create approvals
        approval_pending_1 = Approval(
            project_id=user_project.id,
            resource_type="task",
            resource_id=task1.id,
            requested_by="dev@example.com",
            status="pending"
        )
        approval_pending_2 = Approval(
            project_id=user_project.id,
            resource_type="task",
            resource_id=task2.id,
            requested_by="dev@example.com",
            status="pending"
        )
        approval_approved_1 = Approval(
            project_id=user_project.id,
            resource_type="task",
            resource_id="dummy_id_1",
            requested_by="dev@example.com",
            status="approved",
            approver_id="founder@example.com"
        )
        approval_approved_2 = Approval(
            project_id=user_project.id,
            resource_type="deliverable",
            resource_id="dummy_id_2",
            requested_by="dev@example.com",
            status="approved",
            approver_id="founder@example.com"
        )
        approval_approved_3 = Approval(
            project_id=user_project.id,
            resource_type="task",
            resource_id="dummy_id_3",
            requested_by="dev@example.com",
            status="approved",
            approver_id="founder@example.com"
        )
        approval_rejected_1 = Approval(
            project_id=user_project.id,
            resource_type="task",
            resource_id="dummy_id_4",
            requested_by="dev@example.com",
            status="rejected",
            approver_id="founder@example.com"
        )
        db.add_all([
            approval_pending_1, approval_pending_2,
            approval_approved_1, approval_approved_2, approval_approved_3,
            approval_rejected_1
        ])
        await db.commit()

    return {"project": user_project}


@pytest.mark.asyncio
async def test_count_tasks_by_status(project_with_diverse_tasks):
    """Test counting tasks by status."""
    async with AsyncSessionLocal() as db:
        # Count pending tasks
        pending_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == project_with_diverse_tasks["project"].id) &
                (Task.status == "pending")
            )
        )
        pending_count = pending_q.scalar()

        # Count assigned tasks
        assigned_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == project_with_diverse_tasks["project"].id) &
                (Task.status == "assigned")
            )
        )
        assigned_count = assigned_q.scalar()

        # Count in progress tasks
        in_progress_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == project_with_diverse_tasks["project"].id) &
                (Task.status == "in_progress")
            )
        )
        in_progress_count = in_progress_q.scalar()

        # Count completed tasks
        completed_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == project_with_diverse_tasks["project"].id) &
                (Task.status == "completed")
            )
        )
        completed_count = completed_q.scalar()

    assert pending_count == 2
    assert assigned_count == 3
    assert in_progress_count == 2
    assert completed_count == 1


@pytest.mark.asyncio
async def test_count_deliverables_by_status(project_with_deliverables):
    """Test counting deliverables by status."""
    async with AsyncSessionLocal() as db:
        pending_q = await db.execute(
            select(func.count(Deliverable.id)).where(
                (Deliverable.project_id == project_with_deliverables["project"].id) &
                (Deliverable.status == "pending")
            )
        )
        pending_count = pending_q.scalar()

        in_progress_q = await db.execute(
            select(func.count(Deliverable.id)).where(
                (Deliverable.project_id == project_with_deliverables["project"].id) &
                (Deliverable.status == "in_progress")
            )
        )
        in_progress_count = in_progress_q.scalar()

        approved_q = await db.execute(
            select(func.count(Deliverable.id)).where(
                (Deliverable.project_id == project_with_deliverables["project"].id) &
                (Deliverable.status == "approved")
            )
        )
        approved_count = approved_q.scalar()

    assert pending_count == 2
    assert in_progress_count == 3
    assert approved_count == 1


@pytest.mark.asyncio
async def test_count_approvals_by_status(project_with_approvals):
    """Test counting approvals by status."""
    async with AsyncSessionLocal() as db:
        pending_q = await db.execute(
            select(func.count(Approval.id)).where(
                (Approval.project_id == project_with_approvals["project"].id) &
                (Approval.status == "pending")
            )
        )
        pending_count = pending_q.scalar()

        approved_q = await db.execute(
            select(func.count(Approval.id)).where(
                (Approval.project_id == project_with_approvals["project"].id) &
                (Approval.status == "approved")
            )
        )
        approved_count = approved_q.scalar()

        rejected_q = await db.execute(
            select(func.count(Approval.id)).where(
                (Approval.project_id == project_with_approvals["project"].id) &
                (Approval.status == "rejected")
            )
        )
        rejected_count = rejected_q.scalar()

    assert pending_count == 2
    assert approved_count == 3
    assert rejected_count == 1


@pytest.mark.asyncio
async def test_metrics_project_isolation(user_project, second_user):
    """Test that metrics are isolated by project."""
    async with AsyncSessionLocal() as db:
        from app.db.models import Project

        other_project = Project(name="Other Project", user_id=second_user.id, core_context={})
        db.add(other_project)
        await db.commit()
        await db.refresh(other_project)

        # Add tasks to both projects
        task1 = Task(
            project_id=user_project.id,
            title="Project 1 Task",
            status="pending",
            assigned_agent="developer",
            input_context={}
        )
        task2 = Task(
            project_id=other_project.id,
            title="Project 2 Task",
            status="pending",
            assigned_agent="developer",
            input_context={}
        )
        db.add_all([task1, task2])
        await db.commit()

    # Check metrics for each project
    async with AsyncSessionLocal() as db:
        proj1_pending_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == user_project.id) &
                (Task.status == "pending")
            )
        )
        proj1_pending = proj1_pending_q.scalar()

        proj2_pending_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == other_project.id) &
                (Task.status == "pending")
            )
        )
        proj2_pending = proj2_pending_q.scalar()

    assert proj1_pending == 1
    assert proj2_pending == 1


@pytest.mark.asyncio
async def test_metrics_empty_project(user_project):
    """Test metrics for empty project."""
    async with AsyncSessionLocal() as db:
        pending_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == user_project.id) &
                (Task.status == "pending")
            )
        )
        pending_count = pending_q.scalar()

        deliverables_q = await db.execute(
            select(func.count(Deliverable.id)).where(
                Deliverable.project_id == user_project.id
            )
        )
        deliverables_count = deliverables_q.scalar()

        approvals_q = await db.execute(
            select(func.count(Approval.id)).where(
                Approval.project_id == user_project.id
            )
        )
        approvals_count = approvals_q.scalar()

    assert pending_count == 0
    assert deliverables_count == 0
    assert approvals_count == 0


@pytest.mark.asyncio
async def test_task_metrics_aggregate_in_progress(user_project):
    """Test that in-progress metrics include both 'working' and 'review' stages."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Test",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # Create tasks with different in-progress stages
        task_working = Task(
            project_id=user_project.id,
            plan_id=plan.id,
            title="Working task",
            status="in_progress",
            stage="working",
            assigned_agent="developer",
            input_context={}
        )
        task_review = Task(
            project_id=user_project.id,
            plan_id=plan.id,
            title="Review task",
            status="in_progress",
            stage="review",
            assigned_agent="developer",
            input_context={}
        )
        db.add_all([task_working, task_review])
        await db.commit()

    # For aggregation, both should count as "in-progress"
    async with AsyncSessionLocal() as db:
        in_progress_q = await db.execute(
            select(func.count(Task.id)).where(
                (Task.project_id == user_project.id) &
                (Task.status == "in_progress")
            )
        )
        in_progress_count = in_progress_q.scalar()

    assert in_progress_count == 2


# Import fixtures
import pytest_asyncio
from app.db.models import Project
