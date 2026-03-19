from __future__ import annotations

from app.event_bus.event_bus import EventBus
from app.orchestration.orchestrator import Orchestrator


def bootstrap() -> Orchestrator:
    print("[BOOTSTRAP] Creating EventBus...")
    event_bus = EventBus()

    print("[BOOTSTRAP] Creating Orchestrator...")
    system = Orchestrator(event_bus)

    print("[BOOTSTRAP] System ready")
    return system