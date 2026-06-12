from app.events import types as event_types
from app.events.bus import event_bus
from app.services.memory_sync import SYNC_TRIGGERS, sync_memory_handler


def register_event_handlers() -> None:
    for trigger in SYNC_TRIGGERS:
        event_bus.subscribe(trigger, _wrap_sync_handler)


async def _wrap_sync_handler(payload: dict) -> None:
    await sync_memory_handler(payload)
