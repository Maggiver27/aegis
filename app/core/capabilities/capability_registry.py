from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.core.capabilities.capability_handler import CapabilityHandler


class CapabilityRegistryError(ValueError):
    """Raised when capability registry operations fail."""


@dataclass(slots=True)
class RegisteredCapability:
    """
    Registry entry describing one available system capability.

    Architectural purpose:
    - registry stores stable capability metadata
    - registry points to the concrete handler implementation
    - Action Bus resolves handler by capability_name through this registry
    """

    capability_name: str
    handler: CapabilityHandler
    description: str = ""

    def __post_init__(self) -> None:
        self.capability_name = self.capability_name.strip()

        if not self.capability_name:
            raise CapabilityRegistryError(
                "capability_name must not be empty"
            )

        if not isinstance(self.description, str):
            raise CapabilityRegistryError(
                "description must be a string"
            )

        if not isinstance(self.handler, CapabilityHandler):
            raise CapabilityRegistryError(
                "handler must implement CapabilityHandler"
            )

        if self.handler.capability_name != self.capability_name:
            raise CapabilityRegistryError(
                "handler.capability_name must match registry capability_name"
            )


class CapabilityRegistry:
    """
    Registry of all system capabilities.

    Rules:
    - registers capability handlers under a unique capability_name
    - resolves handlers by capability_name
    - does not execute handlers
    - execution belongs to Action Bus
    """

    def __init__(self) -> None:
        self._capabilities: Dict[str, RegisteredCapability] = {}

    def register(self, capability: RegisteredCapability) -> None:
        if capability.capability_name in self._capabilities:
            raise CapabilityRegistryError(
                f"Capability already registered: {capability.capability_name}"
            )

        self._capabilities[capability.capability_name] = capability

    def get(self, capability_name: str) -> RegisteredCapability:
        normalized_name = capability_name.strip()

        if not normalized_name:
            raise CapabilityRegistryError(
                "capability_name must not be empty"
            )

        if normalized_name not in self._capabilities:
            raise CapabilityRegistryError(
                f"Capability not found: {normalized_name}"
            )

        return self._capabilities[normalized_name]

    def has(self, capability_name: str) -> bool:
        normalized_name = capability_name.strip()
        return bool(normalized_name) and normalized_name in self._capabilities

    def list_names(self) -> list[str]:
        return list(self._capabilities.keys())

    def list_capabilities(self) -> list[RegisteredCapability]:
        return list(self._capabilities.values())