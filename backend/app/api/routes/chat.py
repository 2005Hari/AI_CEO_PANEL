import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import select

from app.api.deps.auth import get_current_user
from app.api.deps.project import get_project_for_user
from app.db.models import User, Project, Session, Message
from app.orchestrator.graph import orchestrator
from app.orchestrator.state import GraphState
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()


class ChatRequest(BaseModel):
    project_id: str
    message: str
    session_id: Optional[str] = None
    mode: str = "advisor"


from app.orchestrator.ceo import ceo_orchestrator_stream

async def sse_generator(
    request: Request,
    chat_req: ChatRequest,
    current_user: User,
    project: Project,
) -> AsyncGenerator[str, None]:
    if chat_req.mode == "ceo":
        try:
            async with AsyncSessionLocal() as db:
                session_id = chat_req.session_id
                if not session_id:
                    session = Session(project_id=project.id)
                    db.add(session)
                    await db.commit()
                    await db.refresh(session)
                    session_id = session.id
                    yield json.dumps({"type": "session_created", "session_id": session_id})

                user_message = Message(
                    session_id=session_id,
                    role="user",
                    content=chat_req.message,
                )
                db.add(user_message)
                await db.commit()

                async for chunk in ceo_orchestrator_stream(project.id, session_id, chat_req.message, db):
                    yield chunk
        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)})
        return

    try:
        async with AsyncSessionLocal() as db:
            session_id = chat_req.session_id
            if not session_id:
                session = Session(project_id=project.id)
                db.add(session)
                await db.commit()
                await db.refresh(session)
                session_id = session.id
                yield json.dumps({"type": "session_created", "session_id": session_id})
            else:
                result = await db.execute(
                    select(Session)
                    .join(Project, Session.project_id == Project.id)
                    .where(
                        Session.id == session_id,
                        Project.user_id == current_user.id,
                    )
                )
                session = result.scalars().first()
                if not session:
                    yield json.dumps({"type": "error", "content": f"Session {session_id} not found"})
                    return

            user_message = Message(
                session_id=session_id,
                role="user",
                content=chat_req.message,
            )
            db.add(user_message)
            await db.commit()

            result = await db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
            )
            db_messages = result.scalars().all()

            graph_messages = []
            for msg in db_messages:
                if msg.role == "user":
                    graph_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    graph_messages.append(AIMessage(content=msg.content))

            initial_state: GraphState = {
                "user_id": current_user.id,
                "project_id": project.id,
                "messages": graph_messages,
                "intent": "",
                "active_agents": [],
                "retrieved_context": "",
                "draft_responses": {},
                "critiques": {},
                "final_consensus": "",
                "mode": chat_req.mode,
            }

            final_consensus = ""
            draft_responses = {}
            critiques_response = {}

            async for output in orchestrator.astream(initial_state):
                if await request.is_disconnected():
                    break

                for node_name, state_update in output.items():
                    if node_name == "analyzer":
                        yield json.dumps({
                            "type": "status",
                            "content": (
                                f"Analyzed intent: {state_update.get('intent', '')}. "
                                f"Waking agents: {', '.join(state_update.get('active_agents', []))}. "
                                "This can take a couple of minutes end to end."
                            ),
                        })
                    elif node_name == "parallel_agents":
                        drafts = state_update.get("draft_responses", {})
                        draft_responses.update(drafts)
                        for agent_key, draft in drafts.items():
                            yield json.dumps({
                                "type": "agent_draft",
                                "agent": agent_key,
                                "content": draft,
                            })
                        # LangGraph only yields a node's output once it has fully
                        # finished, so there is no signal for the next stage
                        # starting unless we say so here — without this, the UI
                        # goes quiet for the entire critic + synthesis phases.
                        yield json.dumps({
                            "type": "status",
                            "content": "Risk Analyst is reviewing the drafts for blind spots...",
                        })
                    elif node_name == "critic":
                        critiques = state_update.get("critiques", {})
                        critiques_response.update(critiques)
                        for agent_key, critique in critiques.items():
                            yield json.dumps({
                                "type": "critic",
                                "agent": agent_key,
                                "content": critique,
                            })
                        yield json.dumps({
                            "type": "status",
                            "content": "Synthesizing the executive consensus...",
                        })
                    elif node_name == "synthesizer":
                        consensus_content = state_update.get("final_consensus", "")
                        final_consensus = consensus_content
                        yield json.dumps({
                            "type": "consensus",
                            "content": consensus_content,
                        })

            if final_consensus and not await request.is_disconnected():
                all_drafts = {**draft_responses, **critiques_response}
                assistant_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=final_consensus,
                    agent_drafts=all_drafts,
                )
                db.add(assistant_message)
                await db.commit()

                from app.services.decisions import log_decision
                from app.services.memory_hooks import on_chat_completed

                await log_decision(
                    db,
                    project_id=project.id,
                    decision_type="strategic",
                    source="boardroom",
                    summary=final_consensus[:500],
                    context={"mode": chat_req.mode, "session_id": session_id},
                    related_session_id=session_id,
                    publish=True,
                )
                await on_chat_completed(
                    project.id,
                    session_id,
                    final_consensus,
                    mode=chat_req.mode,
                )

            yield json.dumps({"type": "done"})

    except Exception as e:
        yield json.dumps({"type": "error", "content": str(e)})


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project_for_user(chat_req.project_id, current_user, db)
    return EventSourceResponse(sse_generator(request, chat_req, current_user, project))
