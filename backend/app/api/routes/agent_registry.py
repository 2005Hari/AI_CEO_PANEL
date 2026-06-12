# backend/app/api/routes/agent_registry.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.auth import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.db.models import AgentDefinition
from app.agents.registry import get_agent_registry, get_agent_definition

router = APIRouter()

class AgentDefinitionResponse(BaseModel):
    id: str
    role: str
    display_name: str
    category: Optional[str] = None
    system_prompt: str
    icon: str
    color: str
    supported_modes: List[str]
    is_system: bool
    
    class Config:
        from_attributes = True


@router.get("/agents", response_model=List[AgentDefinitionResponse])
async def list_agents(
    mode: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all available agents, optionally filtering by operating mode."""
    agents = await get_agent_registry(db, mode=mode)
    return agents

@router.get("/agents/{role}", response_model=AgentDefinitionResponse)
async def get_agent(
    role: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get a specific agent definition."""
    agent = await get_agent_definition(db, role)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
