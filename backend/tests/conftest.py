import asyncio
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("DEV_MOCK_USER_ENABLED", "true")

from app.main import app
from app.db.session import AsyncSessionLocal, sync_engine
from app.db.models import Base, User, Project
from app.api.deps.auth import get_current_user, DEV_MOCK_CLERK_ID


@pytest.fixture(autouse=True)
def register_bus_handlers():
    from app.events.handlers import register_event_handlers
    register_event_handlers()
    yield


@pytest.fixture(autouse=True)
def reset_sse_app_status():
    """Reset sse-starlette singleton event between tests (avoids event loop binding errors)."""
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = asyncio.Event()
    yield
    AppStatus.should_exit_event = asyncio.Event()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    yield
    Base.metadata.drop_all(bind=sync_engine)


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def mock_user(db_session):
    result = await db_session.execute(select(User).where(User.clerk_id == DEV_MOCK_CLERK_ID))
    user = result.scalars().first()
    if not user:
        user = User(clerk_id=DEV_MOCK_CLERK_ID, email="founder@dev.local")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user(db_session):
    result = await db_session.execute(select(User).where(User.clerk_id == "second_user_clerk"))
    user = result.scalars().first()
    if not user:
        user = User(clerk_id="second_user_clerk", email="second@dev.local")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(mock_user):
    async def override_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_project(db_session, mock_user):
    project = Project(name="Test Co", user_id=mock_user.id, core_context={"company_name": "Test Co"})
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
