# backend/app/api/routes/agents.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps.project import get_project_for_user
from app.db.session import get_db
from app.db.models import Project, AgentConfig
from app.agents.instances import AGENTS_MAP

router = APIRouter()

# Schema for response/request
class AgentConfigSchema(BaseModel):
    agent_role: str
    system_prompt: Optional[str] = None
    model_override: Optional[str] = None
    temperature: Optional[float] = None
    is_enabled: bool = True

    class Config:
        from_attributes = True

@router.get("/projects/{project_id}/agents/config", response_model=List[AgentConfigSchema])
async def list_agent_configs(
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve custom overrides merged with code-level defaults for all 5 agents."""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.project_id == project.id)
    )
    overrides = {ac.agent_role: ac for ac in result.scalars().all()}

    configs = []
    for role, agent in AGENTS_MAP.items():
        if role in overrides:
            db_config = overrides[role]
            # If system_prompt is empty or matches default, we can represent it
            configs.append(AgentConfigSchema(
                agent_role=role,
                system_prompt=db_config.system_prompt if db_config.system_prompt is not None else agent.system_prompt,
                model_override=db_config.model_override,
                temperature=db_config.temperature if db_config.temperature is not None else 0.2,
                is_enabled=db_config.is_enabled if db_config.is_enabled is not None else True
            ))
        else:
            configs.append(AgentConfigSchema(
                agent_role=role,
                system_prompt=agent.system_prompt,
                model_override=None,
                temperature=0.2,
                is_enabled=True
            ))

    return configs

@router.put("/projects/{project_id}/agents/config/{agent_role}", response_model=AgentConfigSchema)
async def update_agent_config(
    agent_role: str,
    config_in: AgentConfigSchema,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update agent configuration overrides."""
    if agent_role not in AGENTS_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent role. Supported: {list(AGENTS_MAP.keys())}"
        )

    result = await db.execute(
        select(AgentConfig)
        .where(AgentConfig.project_id == project.id)
        .where(AgentConfig.agent_role == agent_role)
    )
    db_config = result.scalars().first()

    if not db_config:
        db_config = AgentConfig(
            project_id=project.id,
            agent_role=agent_role
        )
        db.add(db_config)

    # Apply overrides (if they match the default, we still save them or keep them)
    db_config.system_prompt = config_in.system_prompt
    db_config.model_override = config_in.model_override
    db_config.temperature = config_in.temperature
    db_config.is_enabled = config_in.is_enabled

    try:
        await db.commit()
        await db.refresh(db_config)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database save failed: {str(e)}"
        )

    # Fetch default agent prompt for fallback output
    agent = AGENTS_MAP[agent_role]
    return AgentConfigSchema(
        agent_role=db_config.agent_role,
        system_prompt=db_config.system_prompt if db_config.system_prompt is not None else agent.system_prompt,
        model_override=db_config.model_override,
        temperature=db_config.temperature if db_config.temperature is not None else 0.2,
        is_enabled=db_config.is_enabled
    )

@router.delete("/projects/{project_id}/agents/config/{agent_role}", status_code=status.HTTP_204_NO_CONTENT)
async def reset_agent_config(
    agent_role: str,
    project: Project = Depends(get_project_for_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset agent configuration to code-level defaults (deletes overrides record)."""
    result = await db.execute(
        select(AgentConfig)
        .where(AgentConfig.project_id == project.id)
        .where(AgentConfig.agent_role == agent_role)
    )
    db_config = result.scalars().first()

    if db_config:
        await db.delete(db_config)
        await db.commit()

    return
