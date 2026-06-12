"""Publish memory-related events from API and orchestrator hooks."""
from typing import Any, Dict, List, Optional

from app.events import types as event_types
from app.events.bus import event_bus


async def _publish(trigger: str, project_id: str, source: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    await event_bus.publish(
        trigger,
        {
            "project_id": project_id,
            "trigger": trigger,
            "source": source,
            **(metadata or {}),
        },
    )


async def on_chat_completed(
    project_id: str,
    session_id: str,
    consensus_summary: str,
    mode: str = "advisor",
) -> None:
    await _publish(
        event_types.CHAT_COMPLETED,
        project_id,
        "boardroom",
        {
            "session_id": session_id,
            "mode": mode,
            "consensus_preview": consensus_summary[:500],
        },
    )


async def on_task_completed(project_id: str, task_id: str, assigned_agent: Optional[str]) -> None:
    await _publish(
        event_types.TASK_COMPLETED,
        project_id,
        "task_engine",
        {"task_id": task_id, "assigned_agent": assigned_agent},
    )


async def on_document_uploaded(project_id: str, document_id: str, filename: str) -> None:
    await _publish(
        event_types.DOCUMENT_UPLOADED,
        project_id,
        "documents",
        {"document_id": document_id, "filename": filename},
    )


async def on_objective_changed(
    project_id: str,
    objective_id: str,
    action: str,
    title: str,
) -> None:
    await _publish(
        event_types.OBJECTIVE_CHANGED,
        project_id,
        "objectives",
        {"objective_id": objective_id, "action": action, "title": title},
    )


async def on_blueprint_updated(project_id: str, updated_fields: List[str]) -> None:
    await _publish(
        event_types.BLUEPRINT_UPDATED,
        project_id,
        "blueprint",
        {"updated_fields": updated_fields},
    )


async def on_discovery_updated(project_id: str, updated_fields: List[str], confidence: float) -> None:
    await _publish(
        event_types.DISCOVERY_UPDATED,
        project_id,
        "discovery",
        {"updated_fields": updated_fields, "confidence": confidence},
    )
