from __future__ import annotations

from app.core.action_bus.action_bus import ActionBus
from app.core.capabilities.capability_bootstrap import (
    build_capability_registry,
)


def main() -> None:
    # budujemy registry przez bootstrap (centralny punkt)
    registry = build_capability_registry()

    print("\n=== REGISTERED CAPABILITIES (BOOTSTRAP) ===")
    print(registry.list())

    action_bus = ActionBus(registry)

    result = action_bus.execute("system.ping")

    print("\n=== BOOTSTRAP TEST RESULT ===")
    print(result)
    print("=== BOOTSTRAP TEST PASSED ===\n")


if __name__ == "__main__":
    main()