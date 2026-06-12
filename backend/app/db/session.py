from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings

# Async Engine (For FastAPI endpoints)
async_engine_kwargs = {}
sync_engine_kwargs = {}

if settings.async_database_uri.startswith("sqlite"):
    async_engine_kwargs["connect_args"] = {"check_same_thread": False}

if settings.sync_database_uri.startswith("sqlite"):
    sync_engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(
    settings.async_database_uri,
    pool_pre_ping=not settings.async_database_uri.startswith("sqlite"),
    echo=False,
    **async_engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

# Sync Engine (For Alembic and some background tasks if needed)
sync_engine = create_engine(
    settings.sync_database_uri,
    pool_pre_ping=not settings.sync_database_uri.startswith("sqlite"),
    echo=False,
    **sync_engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
