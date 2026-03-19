from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class CapabilityInputValidationError(ValueError):
    """Raised when capability input is invalid."""


@dataclass(slots=True)
class CapabilityInput:
    """
    Stable input contract for capability execution.

    Architectural purpose:
    - Action Bus should accept one explicit input object
    - capabilities should not depend on loose dict payloads
    - this object is the execution boundary for intentional actions

    V1 scope:
    - capability_name: unique action/capability name
    - payload: execution arguments
    - metadata: optional transport/runtime metadata
    - request_id: unique request identifier
    - created_at: UTC creation timestamp
    """

    capability_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        self.capability_name = self.capability_name.strip()

        if not self.capability_name:
            raise CapabilityInputValidationError(
                "capability_name must not be empty"
            )

        if not isinstance(self.payload, dict):
            raise CapabilityInputValidationError(
                "payload must be a dict[str, Any]"
            )

        if not isinstance(self.metadata, dict):
            raise CapabilityInputValidationError(
                "metadata must be a dict[str, Any]"
            )

        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise CapabilityInputValidationError(
                "request_id must be a non-empty string"
            )

        if not isinstance(self.created_at, datetime):
            raise CapabilityInputValidationError(
                "created_at must be a datetime instance"
            )

        if self.created_at.tzinfo is None:
            raise CapabilityInputValidationError(
                "created_at must be timezone-aware"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "payload": self.payload,
            "metadata": self.metadata,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityInput":
        if not isinstance(data, dict):
            raise CapabilityInputValidationError(
                "CapabilityInput.from_dict expects a dict"
            )

        created_at_raw = data.get("created_at")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if isinstance(created_at_raw, str)
            else datetime.now(timezone.utc)
        )

        return cls(
            capability_name=str(data.get("capability_name", "")),
            payload=data.get("payload", {}) or {},
            metadata=data.get("metadata", {}) or {},
            request_id=str(data.get("request_id", "") or str(uuid4())),
            created_at=created_at,
        )