import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class EventBus:
    """Lightweight in-process async pub/sub for side effects."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        handlers = list(self._handlers.get(event_type, []))
        if not handlers:
            return
        results = await asyncio.gather(
            *[self._safe_call(handler, event_type, payload) for handler in handlers],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.exception("Event handler failed for %s: %s", event_type, result)

    async def _safe_call(
        self, handler: EventHandler, event_type: str, payload: Dict[str, Any]
    ) -> None:
        try:
            await handler(payload)
        except Exception:
            logger.exception("Handler %s failed on event %s", handler.__name__, event_type)
            raise


event_bus = EventBus()
