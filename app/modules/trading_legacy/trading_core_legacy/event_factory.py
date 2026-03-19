from app.core.event import Event
from app.core.event_types import EventType


from typing import Any

def create_trade_signal(payload: dict[str, Any]) -> Event:
    return Event(
        type=EventType.TRADE_SIGNAL,
        payload=payload,
    )


def create_task_scheduled(payload: dict[str, Any]) -> Event:
    return Event(
        type=EventType.TASK_SCHEDULED,
        payload=payload,
    )


def create_automation_triggered(payload: dict[str, Any]) -> Event:
    return Event(
        type=EventType.AUTOMATION_TRIGGERED,
        payload=payload,
    )


def create_note_created(payload: dict[str, Any]) -> Event:
    return Event(
        type=EventType.NOTE_CREATED,
        payload=payload,
    )


def create_system_health_check(payload: dict[str, Any]) -> Event:
    return Event(
        type=EventType.SYSTEM_HEALTH_CHECK,
        payload=payload,
    )