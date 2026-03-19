from __future__ import annotations

from app.core.action_bus.action_bus import ActionBus
from app.core.capabilities.capability_handler import CapabilityResult
from app.core.capabilities.capability_input import CapabilityInput
from app.core.capabilities.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)


class TestHandler:
    capability_name = "system.test"

    def handle(self, capability_input: CapabilityInput) -> CapabilityResult:
        return CapabilityResult(
            success=True,
            capability_name="system.test",
            data={
                "received_payload": capability_input.payload,
                "received_metadata": capability_input.metadata,
            },
            message="handler executed",
        )


def main() -> None:
    registry = CapabilityRegistry()

    registry.register(
        RegisteredCapability(
            capability_name="system.test",
            handler=TestHandler(),
            description="test capability for action bus",
        )
    )

    action_bus = ActionBus(capability_registry=registry)

    capability_input = CapabilityInput(
        capability_name="system.test",
        payload={"value": 123},
        metadata={"source": "test_action_bus_v1"},
    )

    result = action_bus.execute(capability_input)

    print(result.to_dict())


if __name__ == "__main__":
    main()