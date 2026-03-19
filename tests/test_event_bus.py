from app.core.event import Event
from app.core.event_types import EventType
from app.event_bus.event_bus import EventBus


def test_event_bus_calls_subscriber_for_matching_event_type() -> None:
    bus = EventBus()
    received: list[Event] = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.TRADE_SIGNAL, handler)

    event = Event(
        type=EventType.TRADE_SIGNAL,
        payload={"pair": "EURUSD", "direction": "LONG"},
    )

    bus.publish(event)

    assert len(received) == 1
    assert received[0] == event


def test_event_bus_does_not_call_subscriber_for_other_event_type() -> None:
    bus = EventBus()
    received: list[Event] = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.NOTE_CREATED, handler)

    event = Event(
        type=EventType.TRADE_SIGNAL,
        payload={"pair": "GBPJPY"},
    )

    bus.publish(event)

    assert received == []