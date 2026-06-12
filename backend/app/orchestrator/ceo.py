import json
from typing import AsyncGenerator, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Plan, Task, Deliverable, AgentActivity, DecisionLog
from app.services.context_builder import UnifiedContextBuilder
from app.services.nvidia import nvidia_service

async def ceo_orchestrator_stream(
    project_id: str,
    session_id: str,
    founder_message: str,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    """
    CEO Agent Orchestrator for FounderOS.
    Acts as the primary router. Analyzes founder intent, uses the Digital Company Brain,
    and decides whether to create plans/tasks or simply answer strategically.
    """
    yield json.dumps({"type": "status", "content": "CEO Agent accessing Digital Company Brain..."})

    # 1. Fetch Digital Company Brain Context
    context = await UnifiedContextBuilder.build(db, project_id, rag_query=founder_message, include_rag=True)
    brain_ctx = context.prompt_text

    yield json.dumps({"type": "status", "content": "CEO Agent analyzing request..."})

    # 2. Determine Action (Converse vs Execute)
    system_prompt = (
        "You are the AI CEO of this company. The founder is speaking to you.\n"
        "Your job is to orchestrate the company. You have various departments (Tech, Marketing, Sales, Design, Ops).\n"
        "Analyze the founder's request. If it requires actual work, generate a Plan with Tasks and Deliverables. "
        "If it's just a question, answer it strategically.\n"
        f"--- DIGITAL COMPANY BRAIN ---\n{brain_ctx}\n---------------------------\n"
        "Respond ONLY with a JSON object:\n"
        "{\n"
        '  "action_type": "converse" or "execute",\n'
        '  "response_message": "What you say back to the founder",\n'
        '  "plan_title": "Title of plan (if execute)",\n'
        '  "plan_description": "Description of plan",\n'
        '  "tasks": [{"title": "Task 1", "assigned_department": "technology", "description": "..."}]\n'
        "}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": founder_message}
    ]

    response_text = await nvidia_service.chat_completion(messages, temperature=0.2, max_tokens=2048)

    # Clean and parse JSON
    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        clean_text = "\n".join(lines).strip()

    try:
        payload = json.loads(clean_text)
    except Exception as e:
        yield json.dumps({"type": "error", "content": "CEO Agent failed to process the request."})
        return

    # 3. Stream the response message
    response_msg = payload.get("response_message", "I am processing your request.")
    yield json.dumps({"type": "agent_draft", "agent": "ceo", "content": {"analysis": response_msg, "confidence": 0.9}})
    yield json.dumps({"type": "consensus", "content": response_msg})

    # 4. If action_type is "execute", create Plan and Tasks (Phase 2 will integrate with WorkQueues)
    if payload.get("action_type") == "execute":
        yield json.dumps({"type": "status", "content": "CEO Agent is drafting a department execution plan..."})
        
        plan = Plan(
            project_id=project_id,
            title=payload.get("plan_title", "CEO Execution Plan"),
            description=payload.get("plan_description", ""),
            status="active",
            owner_agent="ceo"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        tasks = payload.get("tasks", [])
        for t in tasks:
            dept_name = t.get("assigned_department", "operations").lower()
            
            task = Task(
                project_id=project_id,
                plan_id=plan.id,
                title=t.get("title", "Task"),
                description=t.get("description", ""),
                assigned_agent=dept_name,
                status="pending"
            )
            db.add(task)
            await db.flush() # Get task.id
            
            # Department routing logic
            from sqlalchemy import select
            from app.db.models import Department, WorkQueue
            
            result = await db.execute(select(Department).where(Department.project_id == project_id, Department.name == dept_name))
            dept = result.scalars().first()
            if not dept:
                dept = Department(project_id=project_id, name=dept_name, manager_agent=f"{dept_name.capitalize()} Manager")
                db.add(dept)
                await db.flush()
                
            queue_entry = WorkQueue(
                department_id=dept.id,
                project_id=project_id,
                task_id=task.id,
                status="queued"
            )
            db.add(queue_entry)
            
            # Log the CEO assigning this to the department
            activity = AgentActivity(
                project_id=project_id,
                task_id=task.id,
                agent_role="ceo",
                activity_type="assigned_task",
                message=f"CEO assigned task '{task.title}' to the {dept.name} department queue."
            )
            db.add(activity)

        await db.commit()
        yield json.dumps({"type": "status", "content": f"Plan '{plan.title}' created and delegated to departments."})
    
    yield json.dumps({"type": "done"})
