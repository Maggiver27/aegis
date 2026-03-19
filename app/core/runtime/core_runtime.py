from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuntimeStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass(slots=True)
class RuntimeSnapshot:
    name: str
    status: RuntimeStatus
    started_at: datetime | None
    stopped_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


class CoreRuntime:
    """MSC-1 Core Runtime with minimal state and lifecycle."""

    def __init__(
        self,
        name: str = "mcgiver-ai-core",
    ) -> None:
        self._name = name
        self._status = RuntimeStatus.CREATED
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._metadata: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> RuntimeStatus:
        return self._status

    def start(self) -> None:
        if self._status == RuntimeStatus.RUNNING:
            return

        self._status = RuntimeStatus.STARTING
        self._started_at = datetime.now(timezone.utc)
        self._stopped_at = None
        self._status = RuntimeStatus.RUNNING

    def stop(self) -> None:
        if self._status == RuntimeStatus.STOPPED:
            return

        self._status = RuntimeStatus.STOPPING
        self._stopped_at = datetime.now(timezone.utc)
        self._status = RuntimeStatus.STOPPED

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            name=self._name,
            status=self._status,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            metadata=dict(self._metadata),
        )