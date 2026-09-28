import asyncio
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal, async_engine
from app.db.models import WorkQueue, Task, Department, AgentActivity, AgentDefinition
from app.api.websockets import manager
from app.core.config import settings
from app.services.tool_registry import registry
from app.services.integrations import IntegrationManager
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage

_llm = None


def get_llm():
    """Lazily construct the NVIDIA-backed LLM client.

    Deferred so that a missing NVIDIA_API_KEY only breaks task execution
    (which needs it) rather than crashing the whole app at startup.
    """
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.3,
            model_kwargs={"parallel_tool_calls": False}
        )
    return _llm

def build_project_tools(project_id: str):
    @tool
    async def execute_integration(tool_name: str, arguments_json: str) -> str:
        """Executes a third-party integration tool.
        Provide the exact tool_name and a JSON string of arguments matching its schema.
        """
        try:
            args = json.loads(arguments_json)
            async with AsyncSessionLocal() as db:
                res = await IntegrationManager.execute_tool_call(project_id, tool_name, args, db)
            return json.dumps(res)
        except Exception as e:
            return f"Error executing integration tool: {str(e)}"

    return [execute_integration]


async def process_queue_item(item_id: str):
    """Processes a single queue item by passing it to the relevant agent with true personas."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkQueue)
            .options(selectinload(WorkQueue.task), selectinload(WorkQueue.department))
            .where(WorkQueue.id == item_id)
        )
        queue_item = result.scalars().first()

        if not queue_item:
            return

        # FIX: Guard against double-pickup — mark processing immediately
        if queue_item.status != "queued":
            return

        task = queue_item.task
        dept = queue_item.department

        # Mark as processing BEFORE any await that could cause a race
        queue_item.status = "processing"
        queue_item.started_at = datetime.utcnow()
        queue_item.assigned_worker = queue_item.assigned_worker or f"{dept.name} Worker"
        task.status = "working"

        activity = AgentActivity(
            project_id=str(queue_item.project_id),  # FIX: str()
            task_id=str(task.id),                    # FIX: str()
            agent_role=queue_item.assigned_worker,
            activity_type="working",
            message=f"{queue_item.assigned_worker} started working on task: '{task.title}'"
        )
        db.add(activity)
        await db.commit()

        # FIX: str(task.id) — UUID objects are not JSON serializable
        await manager.broadcast_to_project(str(queue_item.project_id), {
            "type": "activity_logged",
            "task_id": str(task.id),
            "agent_role": queue_item.assigned_worker,
            "task_title": task.title,
            "status": "working"
        })

        # Fetch true persona
        agent_def_result = await db.execute(
            select(AgentDefinition).where(
                AgentDefinition.display_name == queue_item.assigned_worker
            )
        )
        agent_def = agent_def_result.scalars().first()
        persona_prompt = (
            agent_def.system_prompt
            if agent_def
            else f"You are a specialist worker in the {dept.name} department. "
                 f"You produce high-quality, actionable deliverables. Be specific, practical, and thorough."
        )

        # Fetch dynamic integrations
        providers = await IntegrationManager.get_active_providers(str(queue_item.project_id), db)
        integration_schemas = []
        for provider in providers:
            integration_schemas.extend(provider.get_tools())

        integration_context = ""
        if integration_schemas:
            integration_context = "\n\nAVAILABLE INTEGRATION TOOLS (Use 'execute_integration' to call these):\n"
            for schema in integration_schemas:
                integration_context += (
                    f"- Name: {schema['name']}\n"
                    f"  Description: {schema['description']}\n"
                    f"  Schema: {json.dumps(schema['parameters'])}\n\n"
                )

        # Combine tools
        agent_tools = registry.tools + build_project_tools(str(queue_item.project_id))

        # Instantiate agent with true system persona
        agent_executor = create_react_agent(
            get_llm(),
            agent_tools,
            prompt=persona_prompt
        )

        # Build task prompt — no persona here, it's in state_modifier
        prompt = (
            f"Your current assignment:\n"
            f"Title: {task.title}\n"
            f"Description: {task.description}\n\n"
            f"Context: {json.dumps(task.input_context or {})}\n\n"
            f"Produce the final deliverable output. Be specific, detailed, and actionable. "
            f"Use tools if necessary."
            f"{integration_context}"
        )

        try:
            final_content = ""

            # Broadcast agent started
            await manager.broadcast_to_project(str(queue_item.project_id), {
                "type": "agent_lifecycle",
                "event": "started",
                "task_id": str(task.id),
                "agent_role": queue_item.assigned_worker,
                "task_title": task.title,
            })

            # Stream execution
            async for event in agent_executor.astream(
                {"messages": [("user", prompt)]},
                stream_mode="updates"
            ):
                for node_name, node_state in event.items():
                    messages = node_state.get("messages", [])
                    if not messages:
                        continue

                    msgs = messages if isinstance(messages, list) else [messages]
                    for msg in msgs:
                        if msg.type == "ai":
                            if msg.content:
                                # FIX: str(task.id)
                                await manager.broadcast_to_project(str(queue_item.project_id), {
                                    "type": "agent_stream",
                                    "task_id": str(task.id),
                                    "agent_role": queue_item.assigned_worker,
                                    "stream_type": "thought",
                                    "content": str(msg.content)
                                })
                                final_content = msg.content

                            if getattr(msg, "tool_calls", None):
                                for tc in msg.tool_calls:
                                    await manager.broadcast_to_project(str(queue_item.project_id), {
                                        "type": "agent_stream",
                                        "task_id": str(task.id),
                                        "agent_role": queue_item.assigned_worker,
                                        "stream_type": "tool_call",
                                        "content": f"Using tool: {tc['name']}",
                                        "tool_name": tc['name'],
                                        "tool_args": tc.get('args', {})
                                    })

                        elif msg.type == "tool":
                            await manager.broadcast_to_project(str(queue_item.project_id), {
                                "type": "agent_stream",
                                "task_id": str(task.id),
                                "agent_role": queue_item.assigned_worker,
                                "stream_type": "tool_result",
                                "content": f"Tool '{msg.name}' result received",
                                "tool_name": msg.name,
                            })

            # Save result
            task.output_result = {"content": final_content}
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0

            queue_item.status = "completed"
            queue_item.completed_at = datetime.utcnow()

            activity = AgentActivity(
                project_id=str(queue_item.project_id),
                task_id=str(task.id),
                agent_role=queue_item.assigned_worker,
                activity_type="completed",
                message=f"{queue_item.assigned_worker} completed: '{task.title}'"
            )
            db.add(activity)
            await db.commit()

            await manager.broadcast_to_project(str(queue_item.project_id), {
                "type": "task_completed",
                "task_id": str(task.id),
                "agent_role": queue_item.assigned_worker,
                "task_title": task.title,
                "deliverable_preview": str(final_content)[:300]
            })

        except Exception as e:
            import traceback
            print(f"[worker] FULL ERROR for task {task.id}:", flush=True)
            traceback.print_exc()
            task.status = "failed"
            task.error_message = str(e)
            queue_item.status = "failed"

            activity = AgentActivity(
                project_id=str(queue_item.project_id),
                task_id=str(task.id),
                agent_role=queue_item.assigned_worker,
                activity_type="error",
                message=f"Error: {str(e)}"
            )
            db.add(activity)
            await db.commit()

            await manager.broadcast_to_project(str(queue_item.project_id), {
                "type": "task_failed",
                "task_id": str(task.id),
                "agent_role": queue_item.assigned_worker,
                "error": str(e)
            })

            print(f"[worker] Task {task.id} FAILED: {e}")


async def queue_worker_loop():
    """Background polling loop for the WorkQueue."""
    from sqlalchemy import text
    print("[worker] Queue worker loop started.", flush=True)
    while True:
        item_ids = []
        try:
            # Use a completely fresh connection each poll to defeat SQLite read-caching.
            async with async_engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT id FROM work_queues WHERE status = 'queued' ORDER BY queued_at ASC LIMIT 5")
                )
                item_ids = [row[0] for row in result.fetchall()]
                print(f"[worker] Poll — found {len(item_ids)} queued items", flush=True)

            if item_ids:
                print(f"[worker] Picked up {len(item_ids)} queued item(s).", flush=True)

            for item_id in item_ids:
                asyncio.create_task(process_queue_item(str(item_id)))

        except Exception as e:
            import traceback
            print(f"[worker] Queue worker loop error: {e}", flush=True)
            traceback.print_exc()

        await asyncio.sleep(5)


async def sync_business_twin_loop():
    while True:
        try:
            pass
        except Exception as e:
            print(f"[worker] Twin sync error: {e}")
        await asyncio.sleep(3600)


_worker_task = None
_twin_task = None


def start_worker_loop():
    global _worker_task, _twin_task
    if _worker_task is None:
        loop = asyncio.get_event_loop()
        _worker_task = loop.create_task(queue_worker_loop())
        _twin_task = loop.create_task(sync_business_twin_loop())
        print("[worker] Background tasks started.", flush=True)
