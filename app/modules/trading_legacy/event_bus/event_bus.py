from collections import defaultdict
from typing import Callable

from app.core.event import Event
from app.core.event_types import EventType

EventHandler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            handler(event)