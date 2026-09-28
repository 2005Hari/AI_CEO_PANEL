"""AI Boardroom API: bring any work; the right team is assembled dynamically."""
import copy
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps.auth import get_current_user
from app.boardroom.engine import refine_boardroom, run_boardroom
from app.db.models import Boardroom, User
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()

PERSISTED_FIELDS = ("title", "status", "analysis", "board", "sources", "messages", "decisions", "tasks", "outputs", "history", "error")


class BoardroomCreate(BaseModel):
    objective: str = Field(min_length=3, max_length=4000)
    context: Optional[str] = Field(default=None, max_length=20000)


class RefineRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=3000)


def _serialize(b: Boardroom, full: bool = True) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": b.id, "title": b.title, "objective": b.objective, "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }
    if full:
        board = b.board or {}
        out.update(
            context=b.context, analysis=b.analysis, board=board, sources=b.sources or [],
            messages=b.messages or [], decisions=b.decisions or [], tasks=b.tasks or [],
            outputs=b.outputs or [], history=b.history or [], error=b.error,
        )
    else:
        out["artifact_type"] = (b.outputs[-1]["artifact_type"] if b.outputs else None)
        out["team_size"] = len((b.board or {}).get("agents", []))
    return out


async def _get_owned(db: AsyncSession, boardroom_id: str, user: User) -> Boardroom:
    b = (await db.execute(select(Boardroom).where(Boardroom.id == boardroom_id, Boardroom.user_id == user.id))).scalars().first()
    if not b:
        raise HTTPException(status_code=404, detail="Boardroom not found")
    return b


def _friendly_error(e: Exception) -> str:
    return str(e) or e.__class__.__name__


async def _stream(request: Request, boardroom_id: str, user_id: str, mode: str, feedback: str = "") -> AsyncGenerator[str, None]:
    """Drive the engine, persist as it goes, and relay events as SSE JSON."""
    async with AsyncSessionLocal() as db:
        b = (await db.execute(select(Boardroom).where(Boardroom.id == boardroom_id, Boardroom.user_id == user_id))).scalars().first()
        if not b:
            yield json.dumps({"type": "error", "content": "Boardroom not found"})
            return

        async def persist(fields: Dict[str, Any]) -> None:
            for k in PERSISTED_FIELDS:
                if k in fields:
                    setattr(b, k, copy.deepcopy(fields[k]))  # new object: in-place list edits are invisible to SQLAlchemy
            await db.commit()

        finished = False
        try:
            yield json.dumps({"type": "boardroom_created" if mode == "run" else "boardroom_resumed", "boardroom_id": b.id, "objective": b.objective})
            if mode == "run":
                events = run_boardroom(b.objective, b.context or "", persist)
            else:
                state = _serialize(b)
                events = refine_boardroom(state, feedback, persist)
            async for ev in events:
                if await request.is_disconnected():
                    break
                yield json.dumps(ev)
                if ev.get("type") == "done":
                    finished = True
        except Exception as e:  # noqa: BLE001 - reported to the client and stored
            b.status = "failed" if mode == "run" else "complete"
            b.error = _friendly_error(e)
            await db.commit()
            yield json.dumps({"type": "error", "content": b.error})
        finally:
            if not finished and b.status == "running":
                b.status = "interrupted"
                await db.commit()


@router.post("/boardrooms/stream")
async def create_and_run(
    request: Request,
    body: BoardroomCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = Boardroom(user_id=user.id, objective=body.objective.strip(), context=body.context, title=body.objective.strip()[:120], status="running")
    db.add(b)
    await db.commit()
    return EventSourceResponse(_stream(request, b.id, user.id, "run"))


@router.get("/boardrooms")
async def list_boardrooms(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = (await db.execute(select(Boardroom).where(Boardroom.user_id == user.id).order_by(Boardroom.created_at.desc()))).scalars().all()
    return [_serialize(b, full=False) for b in rows]


@router.get("/boardrooms/{boardroom_id}")
async def get_boardroom(boardroom_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return _serialize(await _get_owned(db, boardroom_id, user))


@router.post("/boardrooms/{boardroom_id}/refine")
async def refine(
    request: Request,
    boardroom_id: str,
    body: RefineRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = await _get_owned(db, boardroom_id, user)
    if not b.outputs:
        raise HTTPException(status_code=409, detail="This boardroom has no deliverable to refine yet.")
    return EventSourceResponse(_stream(request, b.id, user.id, "refine", body.feedback))


@router.delete("/boardrooms/{boardroom_id}", status_code=204)
async def delete_boardroom(boardroom_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.delete(await _get_owned(db, boardroom_id, user))
    await db.commit()
