from __future__ import annotations

from app.core.capabilities.capability_handler import (
    CapabilityHandler,
    CapabilityResult,
)
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
            data={"echo": capability_input.payload},
        )


def main() -> None:
    registry = CapabilityRegistry()

    registry.register(
        RegisteredCapability(
            capability_name="system.test",
            handler=TestHandler(),
            description="test capability",
        )
    )

    print("LIST:", registry.list_names())
    print("DESC:", registry.get("system.test").description)


if __name__ == "__main__":
    main()