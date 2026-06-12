import json
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AgentDefinition, Task, Plan, Deliverable, Department, WorkQueue
from app.services.context_builder import UnifiedContextBuilder
from app.services.nvidia import nvidia_service
from app.api.websockets import manager

def _map_agent_to_department(agent_name: str) -> str:
    if not agent_name:
        return "Operations"
    name_lower = str(agent_name).lower()
    if any(x in name_lower for x in ["dev", "engineer", "tech", "cto"]):
        return "Engineering"
    if any(x in name_lower for x in ["market", "seo", "content", "cmo", "copy"]):
        return "Marketing"
    if any(x in name_lower for x in ["design", "creative", "art"]):
        return "Design"
    if any(x in name_lower for x in ["sale", "lead"]):
        return "Sales"
    return "Operations"

async def create_plan_and_tasks(project_id: str, founder_request: str, db: AsyncSession) -> Dict[str, Any]:
    """Manager v2: generates a Plan, Tasks, and Deliverables for a founder request.
    Expects LLM JSON with optional 'deliverables' list and 'tasks' linked to deliverables by name.
    """
    # Build context
    context = await UnifiedContextBuilder.build(db, project_id, rag_query=founder_request, include_rag=True)
    blueprint_ctx = context.prompt_text

    # Load agents
    result = await db.execute(select(AgentDefinition))
    agents = result.scalars().all()
    agent_descriptions = "\n".join([f"- {a.role}: {a.display_name} ({a.category})" for a in agents])

    prompt = (
        "You are the Project Manager Agent v2. Produce a Plan object with tasks and optional deliverables.\n"
        "Return a JSON object with fields: plan_title, plan_description, deliverables (optional), tasks.\n"
        "Each deliverable: {name, description, deliverable_type}.\n"
        "Each task: {title, description, assigned_agent, priority, deliverable_name (optional), review_required (bool)}\n"
        f"Company Blueprint:\n{blueprint_ctx}\n"
        "CRITICAL: Respond ONLY with valid JSON. No markdown.\n"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": founder_request}
    ]

    response_text = await nvidia_service.chat_completion(messages, temperature=0.2, max_tokens=2048)

    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    try:
        payload = json.loads(clean_text)
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse manager v2 response: {e}", "raw": response_text}

    # Create Plan
    plan = Plan(
        project_id=project_id,
        title=payload.get("plan_title") or payload.get("title") or "Generated Plan",
        description=payload.get("plan_description") or payload.get("description"),
        status="active",
        owner_agent="manager",
        milestones=payload.get("milestones") or [],
        generated_by="manager_v2",
        confidence_score=payload.get("confidence")
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    created_deliverables = {}
    for d in payload.get("deliverables", []):
        dv = Deliverable(
            project_id=project_id,
            plan_id=plan.id,
            deliverable_type=d.get("deliverable_type") or d.get("type") or "generic",
            title=d.get("name") or d.get("title") or "Deliverable",
            status="pending",
            content_markdown=d.get("description") or d.get("desc"),
            created_by_agent="manager_v2",
        )
        db.add(dv)
        created_deliverables[dv.title] = dv

    await db.commit()

    # Pre-fetch existing departments
    dept_result = await db.execute(select(Department).where(Department.project_id == project_id))
    existing_depts = {d.name: d for d in dept_result.scalars().all()}

    created_tasks = []
    for t in payload.get("tasks", []):
        task = Task(
            project_id=project_id,
            plan_id=plan.id,
            title=t.get("title", "Untitled Task"),
            description=t.get("description", ""),
            assigned_agent=t.get("assigned_agent"),
            priority=t.get("priority", "medium"),
            status="assigned",
            input_context={"founder_request": founder_request},
            review_required=bool(t.get("review_required", False)),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        # Link to deliverable if name provided
        deliverable_name = t.get("deliverable_name")
        created_tasks.append((task, deliverable_name))
        
        # Map to department and WorkQueue
        dept_name = _map_agent_to_department(task.assigned_agent)
        if dept_name not in existing_depts:
            new_dept = Department(project_id=project_id, name=dept_name, manager_agent=f"{dept_name} Manager")
            db.add(new_dept)
            await db.commit()
            await db.refresh(new_dept)
            existing_depts[dept_name] = new_dept
            
        dept = existing_depts[dept_name]
        
        queue_entry = WorkQueue(
            project_id=project_id,
            department_id=dept.id,
            task_id=task.id,
            status="queued",
            assigned_worker=task.assigned_agent or f"{dept_name} Worker",
            queued_at=datetime.utcnow()
        )
        db.add(queue_entry)

    await db.commit()

    for task, deliverable_name in created_tasks:
        if deliverable_name and deliverable_name in created_deliverables:
            dv = created_deliverables[deliverable_name]
            dv.task_id = task.id
            db.add(dv)
            await db.commit()

    # Emit WebSockets for the new plan and tasks
    await manager.broadcast_to_project(str(project_id), {
        "type": "plan_created",
        "plan_id": str(plan.id),
        "title": plan.title
    })
    
    await manager.broadcast_to_project(str(project_id), {
        "type": "tasks_created",
        "count": len(created_tasks)
    })

    return {
        "status": "success",
        "plan_id": plan.id,
        "plan_title": plan.title,
        "tasks_created": [{"id": t.id, "title": t.title, "assigned_agent": t.assigned_agent} for t, _ in created_tasks],
        "deliverables_created": [{"id": dv.id, "title": dv.title} for dv in created_deliverables.values()],
    }

