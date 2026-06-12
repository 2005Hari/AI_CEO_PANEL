# backend/app/orchestrator/nodes.py
import asyncio
import json
from typing import Dict, Any, List

from app.orchestrator.state import GraphState
from app.agents.instances import AGENTS_MAP
from app.agents.prompts import (
    JUDGE_AGENT_PROMPT,
    VC_JUDGE_PROMPT,
    ANGEL_INVESTOR_PROMPT,
    SAAS_VC_PROMPT,
    DEEP_TECH_VC_PROMPT,
    GROWTH_VC_PROMPT,
    DEVILS_ADVOCATE_PROMPT
)
from app.services.nvidia import nvidia_service
from app.services.embeddings import similarity_search

VC_PROMPTS_MAP = {
    "visionary": ANGEL_INVESTOR_PROMPT,
    "operations": SAAS_VC_PROMPT,
    "marketing": DEEP_TECH_VC_PROMPT,
    "finance": GROWTH_VC_PROMPT,
    "risk": DEVILS_ADVOCATE_PROMPT
}

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Project

async def analyze_intent(state: GraphState) -> Dict[str, Any]:
    """Analyzes the latest user message to determine intent and required agents using NVIDIA service."""
    mode = state.get("mode", "advisor")
    project_id = state.get("project_id")
    disabled_roles = set()
    
    # Load settings overrides to check for disabled roles
    if project_id:
        from app.db.models import AgentConfig
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AgentConfig)
                .where(AgentConfig.project_id == project_id)
                .where(AgentConfig.is_enabled == False)
            )
            disabled_roles = {c.agent_role for c in result.scalars().all()}
            
    if mode == "pitch":
        # In pitch mode, all active agents participate directly
        active = ["visionary", "operations", "marketing", "finance", "risk"]
        active = [a for a in active if a not in disabled_roles]
        return {
            "intent": "Evaluate pitch deck and investment readiness.",
            "active_agents": active
        }

    # Advisor mode: analyze intent dynamically
    last_msg = state["messages"][-1].content
    prompt = (
        "You are an Intent Analyzer for an executive boardroom of AI agents.\n"
        "Your task is to analyze the user's query and determine the intent and which specialized executive agents are required.\n"
        "Available agents: visionary, operations, marketing, finance, risk.\n"
        "The 'risk' agent should usually be included.\n\n"
        "You MUST respond ONLY with a raw, valid JSON object matching this schema:\n"
        "{\n"
        '  "intent": "Short summary of user\'s strategy goal (string)",\n'
        '  "required_agents": ["visionary", "operations", ... (array of strings)]\n'
        "}\n\n"
        f"Query: {last_msg}"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    try:
        response_text = await nvidia_service.chat_completion(messages, temperature=0.0)
        
        # Parse JSON from response
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
            
        result = json.loads(clean_text)
        intent = str(result.get("intent", last_msg))
        active = list(result.get("required_agents", ["visionary", "operations", "marketing", "finance"]))
    except Exception:
        intent = last_msg
        active = ["visionary", "operations", "marketing", "finance"]
        
    active = [a for a in active if a not in disabled_roles]
    
    # Ensure risk is always there if not empty and not disabled
    if "risk" not in active and active and "risk" not in disabled_roles:
        active.append("risk")
        
    return {
        "intent": intent,
        "active_agents": active
    }

async def retrieve_context(state: GraphState) -> Dict[str, Any]:
    """Loads unified company memory and RAG context (boardroom graph unchanged — inject only)."""
    project_id = state.get("project_id")
    if not project_id:
        return {"retrieved_context": "No project context specified."}

    last_msg = state["messages"][-1].content if state.get("messages") else ""

    async with AsyncSessionLocal() as db:
        try:
            from app.services.context_builder import UnifiedContextBuilder

            context = await UnifiedContextBuilder.build(
                db,
                project_id,
                user_id=state.get("user_id"),
                rag_query=last_msg,
                include_rag=True,
            )
            return {"retrieved_context": context.prompt_text}
        except Exception as e:
            print(f"UnifiedContextBuilder failed, using legacy fallback: {e}")

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if not project or not project.core_context:
            return {"retrieved_context": "No core context found for this project."}

        ctx = project.core_context
        formatted_context = (
            f"Company Name: {project.name}\n"
            f"Value Proposition: {ctx.get('value_proposition', 'N/A')}\n"
            f"Target Audience: {ctx.get('target_audience', 'N/A')}\n"
            f"Technology Stack: {ctx.get('tech_stack', 'N/A')}\n"
            f"Business Model: {ctx.get('business_model', 'N/A')}"
        )
        try:
            memories = await similarity_search(db, project_id, last_msg, limit=3)
            if memories:
                formatted_context += "\n\nRelevant Uploaded Knowledge & Context:\n"
                for idx, mem in enumerate(memories):
                    formatted_context += f"[{idx+1}] {mem.content}\n"
        except Exception as rag_error:
            print(f"RAG similarity search failed: {rag_error}")

        return {"retrieved_context": formatted_context}

async def execute_agents(state: GraphState) -> Dict[str, Any]:
    """Executes the selected agents in parallel."""
    active = state.get("active_agents", [])
    user_query = state["messages"][-1].content
    context = state.get("retrieved_context", "")
    project_id = state.get("project_id")
    
    # Load custom configs
    configs = {}
    if project_id:
        from app.db.models import AgentConfig
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AgentConfig).where(AgentConfig.project_id == project_id)
            )
            configs = {c.agent_role: c for c in result.scalars().all()}
            
    tasks = []
    agent_keys = []
    
    for agent_key in active:
        if agent_key in AGENTS_MAP and agent_key != "risk": # Risk runs later as critic
            agent = AGENTS_MAP[agent_key]
            
            # Apply configs overrides if any, otherwise fallback to active mode defaults
            cfg = configs.get(agent_key)
            default_prompt = VC_PROMPTS_MAP[agent_key] if state.get("mode") == "pitch" else agent.system_prompt
            system_prompt = cfg.system_prompt if (cfg and cfg.system_prompt is not None) else default_prompt
            model = cfg.model_override if cfg else None
            temperature = cfg.temperature if cfg else None
            
            tasks.append(agent.ainvoke(
                user_query=user_query,
                context=context,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature
            ))
            agent_keys.append(agent_key)
            
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    drafts = {}
    for key, result in zip(agent_keys, results):
        if not isinstance(result, Exception):
            drafts[key] = result
        else:
            drafts[key] = {"error": str(result)}
            
    return {"draft_responses": drafts}

async def execute_critic(state: GraphState) -> Dict[str, Any]:
    """Risk agent reviews the drafts."""
    drafts = state.get("draft_responses", {})
    if not drafts:
        return {"critiques": {}}
        
    active = state.get("active_agents", [])
    if "risk" not in active:
        return {"critiques": {}}
        
    user_query = state["messages"][-1].content
    risk_agent = AGENTS_MAP["risk"]
    project_id = state.get("project_id")
    mode = state.get("mode", "advisor")
    
    # Load risk override if any
    system_prompt = None
    model = None
    temperature = None
    if project_id:
        from app.db.models import AgentConfig
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AgentConfig)
                .where(AgentConfig.project_id == project_id)
                .where(AgentConfig.agent_role == "risk")
            )
            cfg = result.scalars().first()
            if cfg:
                system_prompt = cfg.system_prompt
                model = cfg.model_override
                temperature = cfg.temperature
                
    # Fallback to defaults
    if not system_prompt:
        system_prompt = DEVILS_ADVOCATE_PROMPT if mode == "pitch" else risk_agent.system_prompt
                
    # We ask risk agent to critique the drafts
    prompt = f"Review these executive drafts for the query: '{user_query}'\nDrafts: {json.dumps(drafts, indent=2)}\nIdentify critical flaws and risks."
    
    result = await risk_agent.ainvoke(
        user_query=prompt,
        context=state.get("retrieved_context", ""),
        system_prompt=system_prompt,
        model=model,
        temperature=temperature
    )
    return {"critiques": {"risk": result}}

async def synthesize_consensus(state: GraphState) -> Dict[str, Any]:
    """Generates the final markdown consensus using the Judge Agent."""
    drafts = state.get("draft_responses", {})
    critiques = state.get("critiques", {})
    user_query = state["messages"][-1].content
    mode = state.get("mode", "advisor")
    
    judge_prompt = VC_JUDGE_PROMPT if mode == "pitch" else JUDGE_AGENT_PROMPT
    
    prompt = (
        f"{judge_prompt}\n\n"
        f"User Query: {user_query}\n\n"
        f"Executive Drafts:\n{json.dumps(drafts, indent=2)}\n\n"
        f"Critiques (Risk):\n{json.dumps(critiques, indent=2)}\n"
    )
    
    messages = [{"role": "system", "content": prompt}]
    
    response = await nvidia_service.chat_completion(messages, temperature=0.3)
    return {"final_consensus": response}
