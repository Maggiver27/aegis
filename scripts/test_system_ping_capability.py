from __future__ import annotations

from app.core.action_bus.action_bus import ActionBus
from app.core.capabilities.capability_bootstrap import build_capability_registry
from app.core.capabilities.capability_input import CapabilityInput


def main() -> None:
    registry = build_capability_registry()
    action_bus = ActionBus(capability_registry=registry)

    capability_input = CapabilityInput(
        capability_name="system.ping",
        payload={"origin": "test_system_ping_capability"},
        metadata={"test_case": "system_ping"},
    )

    result = action_bus.execute(capability_input)

    print("REGISTERED:", registry.list_names())
    print("RESULT:", result.to_dict())


if __name__ == "__main__":
    main()