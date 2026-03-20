from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.logging.log_level import LogLevel


@dataclass(slots=True)
class LogEntry:
    level: LogLevel
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.trace_id:
            self.trace_id = str(uuid4())
