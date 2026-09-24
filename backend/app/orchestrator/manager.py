# backend/app/orchestrator/manager.py
import json
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import AgentDefinition, Task
from app.services.context_builder import UnifiedContextBuilder
from app.services.nvidia import nvidia_service

async def decompose_and_delegate(
    project_id: str,
    founder_request: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Manager Agent logic to decompose a founder request into a list of agent-assigned tasks.
    """
    # 1. Load unified company memory
    context = await UnifiedContextBuilder.build(db, project_id, rag_query=founder_request, include_rag=True)
    blueprint_ctx = context.prompt_text

    # 2. Load available agents
    result = await db.execute(select(AgentDefinition))
    agents = result.scalars().all()
    
    agent_descriptions = "\n".join([f"- {a.role}: {a.display_name} ({a.category})" for a in agents if not a.is_system or a.role in ["manager"]])

    # 3. LLM call to decompose
    prompt = (
        "You are the Project Manager Agent for a startup.\n"
        "Your job is to take a founder's request, analyze it against the company context, "
        "and break it down into an actionable execution plan consisting of specific tasks.\n"
        "Assign each task to the most appropriate specialized agent from the available list.\n\n"
        f"Available Agents:\n{agent_descriptions}\n\n"
        f"Company Blueprint:\n{blueprint_ctx}\n\n"
        "CRITICAL REQUIREMENT: You MUST respond ONLY with a raw, valid JSON object matching the following structure:\n"
        "{\n"
        '  "plan_summary": "Short summary of the overall execution plan",\n'
        '  "tasks": [\n'
        '    {\n'
        '      "title": "Task title",\n'
        '      "description": "Detailed instructions for the agent",\n'
        '      "assigned_agent": "agent_role_from_list",\n'
        '      "priority": "high|medium|low"\n'
        '    }\n'
        '  ]\n'
        "}\n"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": founder_request}
    ]

    try:
        response_text = await nvidia_service.chat_completion(
            messages,
            temperature=0.2,
            max_tokens=2048
        )
    except Exception as e:
        return {"status": "error", "message": f"Manager LLM call failed: {e}"}

    # Clean potential markdown block wrappers
    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    try:
        plan = json.loads(clean_text)
        
        # 4. Save Tasks to DB
        created_tasks = []
        for task_data in plan.get("tasks", []):
            task = Task(
                project_id=project_id,
                title=task_data.get("title", "Untitled Task"),
                description=task_data.get("description", ""),
                assigned_agent=task_data.get("assigned_agent"),
                priority=task_data.get("priority", "medium"),
                status="assigned",
                input_context={"founder_request": founder_request}
            )
            db.add(task)
            created_tasks.append(task)
            
        await db.commit()
        
        for t in created_tasks:
            await db.refresh(t)
            
        return {
            "status": "success",
            "plan_summary": plan.get("plan_summary", ""),
            "tasks_created": [
                {
                    "id": t.id,
                    "title": t.title,
                    "assigned_agent": t.assigned_agent
                } for t in created_tasks
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "raw_response": response_text
        }
