from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.core.logging.log_entry import LogEntry
from app.core.logging.log_level import LogLevel
from app.core.logging.logger_config import LoggerConfig


class Logger:
    def __init__(self, config: LoggerConfig | None = None) -> None:
        self._config = config or LoggerConfig()

    def log(
        self,
        level: LogLevel,
        message: str,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> LogEntry | None:
        try:
            entry = LogEntry(
                level=level,
                message=message,
                metadata=dict(metadata) if metadata else {},
                trace_id=trace_id or str(uuid4()),
            )

            if self._config.enable_console_output:
                output = {
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level.value,
                    "message": entry.message,
                    "trace_id": entry.trace_id,
                    "metadata": entry.metadata,
                }
                print(json.dumps(output, ensure_ascii=False, sort_keys=True, default=str))

            return entry
        except Exception as exc:
            try:
                print(
                    json.dumps(
                        {
                            "timestamp": "LOGGER_FAILURE",
                            "level": "CRITICAL",
                            "message": "Logger internal failure",
                            "error": str(exc),
                        }
                    )
                )
            except Exception:
                pass
            return None
