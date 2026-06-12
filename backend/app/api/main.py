from fastapi import APIRouter
from app.api.routes import (
    chat, projects, sessions, nvidia, documents, agents, blueprint, discovery,
    tasks, activity, agent_registry, objectives, manager, integrations,
    operating_profile, founder_profile, decisions, approvals, metrics, plans
)

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(sessions.router, prefix="", tags=["sessions"])
api_router.include_router(nvidia.router, prefix="", tags=["nvidia"])
api_router.include_router(documents.router, prefix="", tags=["documents"])
api_router.include_router(agents.router, prefix="", tags=["agents"])
api_router.include_router(blueprint.router, prefix="", tags=["blueprint"])
api_router.include_router(discovery.router, prefix="", tags=["discovery"])
api_router.include_router(tasks.router, prefix="", tags=["tasks"])
api_router.include_router(activity.router, prefix="", tags=["activity"])
api_router.include_router(agent_registry.router, prefix="", tags=["agent_registry"])
api_router.include_router(objectives.router, prefix="", tags=["objectives"])
api_router.include_router(manager.router, prefix="", tags=["manager"])
api_router.include_router(integrations.router, prefix="", tags=["integrations"])
api_router.include_router(operating_profile.router, prefix="", tags=["operating_profile"])
api_router.include_router(founder_profile.router, prefix="", tags=["founder_profile"])
api_router.include_router(decisions.router, prefix="", tags=["decisions"])
api_router.include_router(approvals.router, prefix="", tags=["approvals"])
api_router.include_router(metrics.router, prefix="", tags=["metrics"])
api_router.include_router(plans.router, prefix="", tags=["plans"])

from app.api.websockets import router as ws_router
api_router.include_router(ws_router, prefix="", tags=["websockets"])
