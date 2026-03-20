from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoggerConfig:
    enable_console_output: bool = True
