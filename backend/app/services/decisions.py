"""Decision log helpers."""
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DecisionLog
from app.events.bus import event_bus
from app.events import types as event_types


async def log_decision(
    db: AsyncSession,
    *,
    project_id: str,
    decision_type: str,
    source: str,
    summary: str,
    context: Optional[Dict[str, Any]] = None,
    source_agent: Optional[str] = None,
    related_task_id: Optional[str] = None,
    related_session_id: Optional[str] = None,
    related_deliverable_id: Optional[str] = None,
    publish: bool = True,
) -> DecisionLog:
    decision = DecisionLog(
        project_id=project_id,
        decision_type=decision_type,
        source=source,
        source_agent=source_agent,
        summary=summary,
        context=context or {},
        related_task_id=related_task_id,
        related_session_id=related_session_id,
        related_deliverable_id=related_deliverable_id,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)

    if publish:
        await event_bus.publish(
            event_types.DECISION_LOGGED,
            {
                "project_id": project_id,
                "decision_id": decision.id,
                "decision_type": decision_type,
                "source": source,
                "summary": summary,
            },
        )
    return decision
