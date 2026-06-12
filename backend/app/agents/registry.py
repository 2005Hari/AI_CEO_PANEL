# backend/app/agents/registry.py
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AgentDefinition

# Hardcoded seed data for agents if DB is empty
SEED_AGENTS = [
    {
        "role": "business_strategist",
        "display_name": "Business Strategist",
        "category": "strategy",
        "system_prompt": "You are a Business Strategist focused on market positioning, revenue models, and growth.",
        "icon": "📈",
        "color": "#3b82f6",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "marketing_director",
        "display_name": "Marketing Director",
        "category": "marketing",
        "system_prompt": "You are a Marketing Director focused on branding, user acquisition, and GTM strategies.",
        "icon": "🎯",
        "color": "#ec4899",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "technical_architect",
        "display_name": "Technical Architect",
        "category": "engineering",
        "system_prompt": "You are a Technical Architect focused on system design, tech stack selection, and scalability.",
        "icon": "⚙️",
        "color": "#8b5cf6",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "ui_ux_designer",
        "display_name": "UI/UX Designer",
        "category": "creative",
        "system_prompt": "You are a UI/UX Designer focused on user experience, interface design, and product usability.",
        "icon": "🎨",
        "color": "#f59e0b",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "finance_analyst",
        "display_name": "Finance Analyst",
        "category": "operations",
        "system_prompt": "You are a Finance Analyst focused on budgeting, financial modeling, and risk mitigation.",
        "icon": "💰",
        "color": "#10b981",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "operations_manager",
        "display_name": "Operations Manager",
        "category": "operations",
        "system_prompt": "You are an Operations Manager focused on process efficiency, resource allocation, and team management.",
        "icon": "🏭",
        "color": "#64748b",
        "supported_modes": ["business"],
        "is_system": True
    },
    {
        "role": "risk_analyst",
        "display_name": "Risk Analyst",
        "category": "strategy",
        "system_prompt": "You are a Risk Analyst focused on identifying vulnerabilities, legal risks, and competitive threats.",
        "icon": "⚠️",
        "color": "#ef4444",
        "supported_modes": ["startup", "business"],
        "is_system": True
    },
    {
        "role": "manager",
        "display_name": "Project Manager",
        "category": "system",
        "system_prompt": "You are the Project Manager orchestrating tasks, breaking down goals, and delegating to specialized agents.",
        "icon": "📋",
        "color": "#14b8a6",
        "supported_modes": ["startup", "business"],
        "is_system": True
    }
]


async def get_agent_registry(db: AsyncSession, mode: Optional[str] = None) -> List[AgentDefinition]:
    """Retrieve all agents, optionally filtered by mode, seeding them if missing."""
    result = await db.execute(select(AgentDefinition))
    agents = result.scalars().all()
    
    # Seed if empty
    if not agents:
        for seed_data in SEED_AGENTS:
            agent = AgentDefinition(**seed_data)
            db.add(agent)
        await db.commit()
        
        result = await db.execute(select(AgentDefinition))
        agents = result.scalars().all()
        
    if mode:
        # Filter agents by mode using simple python loop
        # Supported modes is JSON list
        agents = [a for a in agents if mode in (a.supported_modes or [])]
        
    return agents

async def get_agent_definition(db: AsyncSession, role: str) -> Optional[AgentDefinition]:
    """Get a specific agent definition by role."""
    # Ensure seeded
    await get_agent_registry(db)
    
    result = await db.execute(select(AgentDefinition).where(AgentDefinition.role == role))
    return result.scalars().first()
