from app.core.event import Event


def log_event(event: Event) -> None:
    print(f"[EVENT] {event.type} -> {event.payload}")