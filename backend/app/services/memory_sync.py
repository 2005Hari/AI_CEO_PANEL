"""Memory synchronization — reacts to bus events and records audit trail."""
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MemoryUpdateEvent
from app.db.session import AsyncSessionLocal
from app.events import types as event_types
from app.events.bus import event_bus
from app.services.operating_profile import sync_operating_profile_from_blueprint


async def record_memory_update(
    db: AsyncSession,
    *,
    project_id: str,
    trigger: str,
    source: str,
    field_updates: Dict[str, Any],
    metadata: Dict[str, Any] | None = None,
) -> MemoryUpdateEvent:
    event = MemoryUpdateEvent(
        project_id=project_id,
        trigger=trigger,
        source=source,
        field_updates=field_updates,
        metadata_json=metadata or {},
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def sync_memory_handler(payload: Dict[str, Any]) -> None:
    """Sync operating profile from blueprint and record memory update."""
    project_id = payload.get("project_id")
    if not project_id:
        return

    trigger = payload.get("trigger", "unknown")
    source = payload.get("source", "system")

    updated_fields: List[str] = []
    profile_version = 0

    async with AsyncSessionLocal() as db:
        profile, updated_fields = await sync_operating_profile_from_blueprint(db, project_id)
        profile_version = profile.version or 0
        await record_memory_update(
            db,
            project_id=project_id,
            trigger=trigger,
            source=source,
            field_updates={"synced_fields": updated_fields, "profile_version": profile_version},
            metadata=payload,
        )

    await event_bus.publish(
        event_types.MEMORY_UPDATED,
        {
            "project_id": project_id,
            "trigger": trigger,
            "updated_at": datetime.utcnow().isoformat(),
            "field_count": len(updated_fields),
            "profile_version": profile_version,
        },
    )


SYNC_TRIGGERS = {
    event_types.CHAT_COMPLETED,
    event_types.TASK_COMPLETED,
    event_types.DOCUMENT_UPLOADED,
    event_types.OBJECTIVE_CHANGED,
    event_types.BLUEPRINT_UPDATED,
    event_types.DISCOVERY_UPDATED,
    event_types.DECISION_LOGGED,
}
