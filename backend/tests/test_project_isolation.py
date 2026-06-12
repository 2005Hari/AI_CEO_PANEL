import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.api.deps.auth import get_current_user
from app.db.models import Project
from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_project(mock_user, second_user, user_project):
    async def override_second():
        return second_user

    app.dependency_overrides[get_current_user] = override_second
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/projects/{user_project.id}")
    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_projects_scoped_to_user(client, mock_user, second_user, user_project):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(Project.name == "Other Co", Project.user_id == second_user.id)
        )
        if not result.scalars().first():
            db.add(Project(name="Other Co", user_id=second_user.id, core_context={}))
            await db.commit()

    response = await client.get("/api/v1/projects/")
    assert response.status_code == 200
    data = response.json()
    project_ids = {p["id"] for p in data}
    project_names = {p["name"] for p in data}
    assert user_project.id in project_ids
    assert "Other Co" not in project_names


@pytest.mark.asyncio
async def test_create_project_assigns_current_user(client, mock_user):
    response = await client.post("/api/v1/projects/", json={"name": "New Startup", "core_context": {}})
    assert response.status_code == 201
    project_id = response.json()["id"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        assert project.user_id == mock_user.id
