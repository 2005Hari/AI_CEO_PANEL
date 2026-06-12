"""Tests for Plans API and CRUD operations."""
import pytest
from sqlalchemy import select
import pytest_asyncio

from app.db.models import Plan, Task
from app.db.session import AsyncSessionLocal


@pytest_asyncio.fixture
async def project_with_plans(user_project):
    """Create a project with multiple plans."""
    async with AsyncSessionLocal() as db:
        plan1 = Plan(
            project_id=user_project.id,
            title="MVP Launch Plan",
            description="Plan for launching MVP",
            status="active",
            owner_agent="manager",
            milestones=["Week 1: Design", "Week 2: Development", "Week 3: Launch"],
            generated_by="manager_v2",
            confidence_score=0.85
        )
        db.add(plan1)

        plan2 = Plan(
            project_id=user_project.id,
            title="Marketing Strategy",
            description="First quarter marketing plan",
            status="active",
            owner_agent="manager",
            milestones=["Month 1: Content creation", "Month 2: Social media", "Month 3: Analytics"],
            generated_by="manager_v2",
            confidence_score=0.72
        )
        db.add(plan2)

        plan3 = Plan(
            project_id=user_project.id,
            title="Completed Plan",
            description="Already completed",
            status="completed",
            owner_agent="manager",
            generated_by="manager_v2",
            confidence_score=0.90
        )
        db.add(plan3)

        await db.commit()
        await db.refresh(plan1)
        await db.refresh(plan2)
        await db.refresh(plan3)

    return {"project": user_project, "plan1": plan1, "plan2": plan2, "plan3": plan3}


@pytest.mark.asyncio
async def test_create_plan(user_project):
    """Test creating a plan."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Test Plan",
            description="Test description",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

    assert plan.id is not None
    assert plan.title == "Test Plan"
    assert plan.status == "active"

    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan.id))
        fetched = plan_q.scalars().first()
        assert fetched is not None
        assert fetched.title == "Test Plan"


@pytest.mark.asyncio
async def test_list_plans_for_project(project_with_plans):
    """Test listing all plans for a project."""
    async with AsyncSessionLocal() as db:
        plans_q = await db.execute(select(Plan).where(Plan.project_id == project_with_plans["project"].id))
        plans = plans_q.scalars().all()

    assert len(plans) == 3
    titles = {p.title for p in plans}
    assert "MVP Launch Plan" in titles
    assert "Marketing Strategy" in titles
    assert "Completed Plan" in titles


@pytest.mark.asyncio
async def test_get_single_plan(project_with_plans):
    """Test fetching a single plan."""
    plan_id = project_with_plans["plan1"].id

    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_q.scalars().first()

    assert plan is not None
    assert plan.title == "MVP Launch Plan"
    assert plan.description == "Plan for launching MVP"


@pytest.mark.asyncio
async def test_plan_with_tasks(user_project):
    """Test plan with associated tasks."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Plan with Tasks",
            description="Plan containing tasks",
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
            title="Task 1",
            assigned_agent="developer",
            status="assigned",
            input_context={}
        )
        task2 = Task(
            project_id=user_project.id,
            plan_id=plan.id,
            title="Task 2",
            assigned_agent="designer",
            status="assigned",
            input_context={}
        )
        db.add_all([task1, task2])
        await db.commit()

    # Fetch plan with tasks
    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan.id))
        fetched_plan = plan_q.scalars().first()

        tasks_q = await db.execute(select(Task).where(Task.plan_id == plan.id))
        tasks = tasks_q.scalars().all()

    assert len(tasks) == 2
    assert all(t.plan_id == fetched_plan.id for t in tasks)


@pytest.mark.asyncio
async def test_plan_status_transitions(user_project):
    """Test plan status changes."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Status Test Plan",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        plan_id = plan.id

    # Change status to completed
    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_q.scalars().first()
        plan.status = "completed"
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

    assert plan.status == "completed"

    # Verify persistence
    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan_id))
        fetched = plan_q.scalars().first()
        assert fetched.status == "completed"


@pytest.mark.asyncio
async def test_plan_with_milestones(user_project):
    """Test plan milestones are persisted."""
    milestones = [
        "Week 1: Design",
        "Week 2: Development",
        "Week 3: Testing",
        "Week 4: Launch"
    ]

    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="Milestone Plan",
            status="active",
            owner_agent="manager",
            milestones=milestones,
            generated_by="manager_v2"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        plan_id = plan.id

    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan_id))
        fetched = plan_q.scalars().first()
        assert fetched.milestones == milestones


@pytest.mark.asyncio
async def test_plan_confidence_score(user_project):
    """Test plan confidence score tracking."""
    async with AsyncSessionLocal() as db:
        plan = Plan(
            project_id=user_project.id,
            title="High Confidence Plan",
            status="active",
            owner_agent="manager",
            confidence_score=0.95,
            generated_by="manager_v2"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        plan_id = plan.id

    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == plan_id))
        fetched = plan_q.scalars().first()
        assert fetched.confidence_score == 0.95


@pytest.mark.asyncio
async def test_plan_generated_by_field(user_project):
    """Test tracking which agent generated the plan."""
    async with AsyncSessionLocal() as db:
        plan1 = Plan(
            project_id=user_project.id,
            title="Manager v2 Plan",
            status="active",
            owner_agent="manager",
            generated_by="manager_v2"
        )
        plan2 = Plan(
            project_id=user_project.id,
            title="Manual Plan",
            status="active",
            owner_agent="manager",
            generated_by="manual"
        )
        db.add_all([plan1, plan2])
        await db.commit()
        await db.refresh(plan1)
        await db.refresh(plan2)

    async with AsyncSessionLocal() as db:
        manager_plans_q = await db.execute(
            select(Plan).where(
                (Plan.project_id == user_project.id) &
                (Plan.generated_by == "manager_v2")
            )
        )
        manager_plans = manager_plans_q.scalars().all()

    assert len(manager_plans) == 1
    assert manager_plans[0].title == "Manager v2 Plan"


@pytest.mark.asyncio
async def test_plan_project_isolation(user_project, second_user):
    """Test plans are isolated by project."""
    async with AsyncSessionLocal() as db:
        from app.db.models import Project

        other_project = Project(name="Other Project", user_id=second_user.id, core_context={})
        db.add(other_project)
        await db.commit()
        await db.refresh(other_project)

        plan1 = Plan(
            project_id=user_project.id,
            title="Project 1 Plan",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        plan2 = Plan(
            project_id=other_project.id,
            title="Project 2 Plan",
            status="active",
            owner_agent="manager",
            generated_by="test"
        )
        db.add_all([plan1, plan2])
        await db.commit()

    async with AsyncSessionLocal() as db:
        user1_plans_q = await db.execute(select(Plan).where(Plan.project_id == user_project.id))
        user1_plans = user1_plans_q.scalars().all()

        user2_plans_q = await db.execute(select(Plan).where(Plan.project_id == other_project.id))
        user2_plans = user2_plans_q.scalars().all()

    assert len(user1_plans) == 1
    assert user1_plans[0].title == "Project 1 Plan"

    assert len(user2_plans) == 1
    assert user2_plans[0].title == "Project 2 Plan"


# Import fixtures
import pytest_asyncio
from app.db.models import Project
