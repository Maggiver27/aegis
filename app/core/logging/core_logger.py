from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class CoreLogger:
    """
    MSC step 3: Core Logging / Audit Foundation

    Responsibility:
    - provide minimal structured logging
    - timestamp every log entry
    - keep interface simple

    Non-responsibility:
    - no file persistence (yet)
    - no external logging frameworks
    - no config-based routing (yet)
    """

    def __init__(self, component: str = "core") -> None:
        self._component = component

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def info(self, message: str, **context: Any) -> None:
        self._log("INFO", message, context)

    def warning(self, message: str, **context: Any) -> None:
        self._log("WARNING", message, context)

    def error(self, message: str, **context: Any) -> None:
        self._log("ERROR", message, context)

    def _log(self, level: str, message: str, context: dict[str, Any]) -> None:
        timestamp = self._now()

        log_entry = {
            "ts": timestamp,
            "level": level,
            "component": self._component,
            "message": message,
            "context": context,
        }

        print(log_entry)