from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.core.capabilities.capability_input import CapabilityInput


@dataclass(slots=True)
class CapabilityResult:
    """
    Standard result returned by a capability handler.

    Architectural purpose:
    - Action Bus receives one stable result shape
    - handlers do not return loose, inconsistent values
    - result can later be extended with tracing, metrics, and errors
    """

    success: bool
    capability_name: str
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "capability_name": self.capability_name,
            "data": self.data,
            "message": self.message,
            "metadata": self.metadata,
        }


@runtime_checkable
class CapabilityHandler(Protocol):
    """
    Stable execution contract for capability handlers.

    Rules:
    - every handler must expose a unique capability_name
    - every handler must accept CapabilityInput
    - every handler must return CapabilityResult
    """

    capability_name: str

    def handle(self, capability_input: CapabilityInput) -> CapabilityResult:
        """
        Execute the capability using the provided input contract.
        """
        ...