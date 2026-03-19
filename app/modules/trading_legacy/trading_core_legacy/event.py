from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.event_types import EventType


@dataclass(slots=True)
class Event:
    type: EventType
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))