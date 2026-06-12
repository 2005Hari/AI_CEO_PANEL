"""Tests for Manager v2 orchestrator (plan generation)."""
import json
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select
import pytest_asyncio

from app.db.models import Plan, Task, Deliverable, CompanyBlueprint, CompanyOperatingProfile
from app.db.session import AsyncSessionLocal
from app.orchestrator.manager_v2 import create_plan_and_tasks


@pytest_asyncio.fixture
async def project_with_blueprint(user_project):
    """Create a project with blueprint and operating profile."""
    async with AsyncSessionLocal() as db:
        blueprint = CompanyBlueprint(
            project_id=user_project.id,
            company_name="TechFlow",
            industry="SaaS",
            value_proposition="AI-powered workflow automation",
            target_audience="SMBs",
            growth_stage="mvp",
            current_goals=["Launch landing page", "Get first 10 users"],
            current_problems=["Customer acquisition", "Product-market fit"],
        )
        db.add(blueprint)

        profile = CompanyOperatingProfile(
            project_id=user_project.id,
            company_name="TechFlow",
            industry="SaaS",
            business_model="Subscription",
            team_size=2,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(blueprint)
        await db.refresh(profile)
    return user_project


@pytest.mark.asyncio
async def test_manager_v2_creates_plan_with_tasks(project_with_blueprint):
    """Test Manager v2 generates plan and creates tasks."""
    mock_response = json.dumps({
        "plan_title": "Landing Page & Marketing MVP",
        "plan_description": "Create landing page, pricing, and initial marketing strategy",
        "deliverables": [
            {
                "name": "Landing Page",
                "description": "Home page with CTA",
                "deliverable_type": "frontend"
            },
            {
                "name": "Marketing Copy",
                "description": "Website copy and email templates",
                "deliverable_type": "content"
            }
        ],
        "tasks": [
            {
                "title": "Design landing page mockup",
                "description": "Create Figma design for landing page",
                "assigned_agent": "designer",
                "priority": "high",
                "deliverable_name": "Landing Page",
                "review_required": True
            },
            {
                "title": "Implement landing page",
                "description": "Build React component for landing page",
                "assigned_agent": "developer",
                "priority": "high",
                "deliverable_name": "Landing Page",
                "review_required": True
            },
            {
                "title": "Write marketing copy",
                "description": "Create compelling copy for website",
                "assigned_agent": "marketing",
                "priority": "medium",
                "deliverable_name": "Marketing Copy",
                "review_required": True
            }
        ]
    })

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Create a landing page and marketing strategy",
                db=db
            )

    assert result["status"] == "success"
    assert "plan_id" in result
    assert result["plan_title"] == "Landing Page & Marketing MVP"
    assert len(result["tasks_created"]) == 3
    assert len(result["deliverables_created"]) == 2

    # Verify in database
    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == result["plan_id"]))
        plan = plan_q.scalars().first()
        assert plan is not None
        assert plan.title == "Landing Page & Marketing MVP"
        assert plan.status == "active"
        assert plan.owner_agent == "manager"

        tasks_q = await db.execute(select(Task).where(Task.plan_id == plan.id))
        tasks = tasks_q.scalars().all()
        assert len(tasks) == 3
        assert all(t.status == "assigned" for t in tasks)
        assert any(t.assigned_agent == "designer" for t in tasks)
        assert any(t.assigned_agent == "developer" for t in tasks)
        assert any(t.assigned_agent == "marketing" for t in tasks)
        assert all(t.review_required for t in tasks)

        deliverables_q = await db.execute(select(Deliverable).where(Deliverable.plan_id == plan.id))
        deliverables = deliverables_q.scalars().all()
        assert len(deliverables) == 2
        assert all(d.status == "pending" for d in deliverables)


@pytest.mark.asyncio
async def test_manager_v2_links_tasks_to_deliverables(project_with_blueprint):
    """Test that tasks are linked to deliverables by name."""
    mock_response = json.dumps({
        "plan_title": "Website Redesign",
        "plan_description": "Redesign website",
        "deliverables": [
            {
                "name": "New Homepage",
                "description": "Redesigned homepage",
                "deliverable_type": "frontend"
            }
        ],
        "tasks": [
            {
                "title": "Design homepage",
                "description": "Create design",
                "assigned_agent": "designer",
                "priority": "high",
                "deliverable_name": "New Homepage",
                "review_required": True
            }
        ]
    })

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Redesign website",
                db=db
            )

    assert result["status"] == "success"

    # Verify task-deliverable link
    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == result["plan_id"]))
        plan = plan_q.scalars().first()

        deliverables_q = await db.execute(select(Deliverable).where(Deliverable.plan_id == plan.id))
        deliverables = deliverables_q.scalars().all()
        assert len(deliverables) == 1

        deliverable = deliverables[0]
        assert deliverable.task_id is not None

        task_q = await db.execute(select(Task).where(Task.id == deliverable.task_id))
        task = task_q.scalars().first()
        assert task.title == "Design homepage"


@pytest.mark.asyncio
async def test_manager_v2_handles_malformed_json(project_with_blueprint):
    """Test Manager v2 handles invalid JSON response."""
    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = "This is not JSON"

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Create a plan",
                db=db
            )

    assert result["status"] == "error"
    assert "Failed to parse" in result["message"]


@pytest.mark.asyncio
async def test_manager_v2_handles_markdown_wrapped_json(project_with_blueprint):
    """Test Manager v2 unwraps markdown-formatted JSON."""
    mock_response = """```json
{
    "plan_title": "Test Plan",
    "plan_description": "Test",
    "tasks": [
        {
            "title": "Test Task",
            "description": "Do something",
            "assigned_agent": "developer",
            "priority": "medium",
            "review_required": false
        }
    ]
}
```"""

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Create a plan",
                db=db
            )

    assert result["status"] == "success"
    assert result["plan_title"] == "Test Plan"


@pytest.mark.asyncio
async def test_manager_v2_empty_deliverables_list(project_with_blueprint):
    """Test Manager v2 handles plans without deliverables."""
    mock_response = json.dumps({
        "plan_title": "Simple Plan",
        "plan_description": "No deliverables",
        "deliverables": [],
        "tasks": [
            {
                "title": "Research task",
                "description": "Do research",
                "assigned_agent": "operations",
                "priority": "low",
                "review_required": False
            }
        ]
    })

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Research market",
                db=db
            )

    assert result["status"] == "success"
    assert len(result["deliverables_created"]) == 0
    assert len(result["tasks_created"]) == 1


@pytest.mark.asyncio
async def test_manager_v2_multiple_tasks_single_deliverable(project_with_blueprint):
    """Test multiple tasks assigned to same deliverable."""
    mock_response = json.dumps({
        "plan_title": "Website Launch",
        "plan_description": "Launch website",
        "deliverables": [
            {
                "name": "Website",
                "description": "Complete website",
                "deliverable_type": "frontend"
            }
        ],
        "tasks": [
            {
                "title": "Design pages",
                "assigned_agent": "designer",
                "priority": "high",
                "deliverable_name": "Website",
                "review_required": True
            },
            {
                "title": "Code frontend",
                "assigned_agent": "developer",
                "priority": "high",
                "deliverable_name": "Website",
                "review_required": True
            },
            {
                "title": "Setup hosting",
                "assigned_agent": "developer",
                "priority": "high",
                "deliverable_name": "Website",
                "review_required": False
            }
        ]
    })

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Launch website",
                db=db
            )

    assert result["status"] == "success"
    assert len(result["tasks_created"]) == 3

    async with AsyncSessionLocal() as db:
        deliverables_q = await db.execute(select(Deliverable).where(Deliverable.plan_id == result["plan_id"]))
        deliverables = deliverables_q.scalars().all()
        assert len(deliverables) == 1


@pytest.mark.asyncio
async def test_manager_v2_preserves_confidence_score(project_with_blueprint):
    """Test Manager v2 stores confidence score."""
    mock_response = json.dumps({
        "plan_title": "Plan with confidence",
        "plan_description": "Test",
        "confidence": 0.85,
        "tasks": []
    })

    with patch("app.services.nvidia.nvidia_service.chat_completion") as mock_chat:
        mock_chat.return_value = mock_response

        async with AsyncSessionLocal() as db:
            result = await create_plan_and_tasks(
                project_id=project_with_blueprint.id,
                founder_request="Create plan",
                db=db
            )

    async with AsyncSessionLocal() as db:
        plan_q = await db.execute(select(Plan).where(Plan.id == result["plan_id"]))
        plan = plan_q.scalars().first()
        assert plan.confidence_score == 0.85


# Import pytest_asyncio for fixtures
import pytest_asyncio
