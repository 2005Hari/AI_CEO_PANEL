from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from contextlib import asynccontextmanager
from app.db.session import sync_engine
from app.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.USE_SQLITE:
        Base.metadata.create_all(bind=sync_engine)
    else:
        from pathlib import Path
        from alembic import command
        from alembic.config import Config
        alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
        command.upgrade(Config(str(alembic_ini)), "head")

    from app.events.handlers import register_event_handlers
    register_event_handlers()
    
    from app.orchestrator.worker_loop import start_worker_loop
    start_worker_loop()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from app.api.main import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
