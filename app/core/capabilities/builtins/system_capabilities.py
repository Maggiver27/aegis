from __future__ import annotations

from app.core.capabilities.capability_handler import CapabilityResult
from app.core.capabilities.capability_input import CapabilityInput
from app.core.capabilities.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)


class SystemPingHandler:
    capability_name = "system.ping"

    def handle(self, capability_input: CapabilityInput) -> CapabilityResult:
        return CapabilityResult(
            success=True,
            capability_name=self.capability_name,
            data={
                "response": "pong",
                "request_payload": capability_input.payload,
            },
            message="system ping executed",
        )


def register_system_capabilities(registry: CapabilityRegistry) -> None:
    """
    Register all built-in system capabilities.

    This is the Core -> CapabilityRegistry entry point
    for built-in capability wiring.
    """

    registry.register(
        RegisteredCapability(
            capability_name="system.ping",
            handler=SystemPingHandler(),
            description="Basic health check capability",
        )
    )