from __future__ import annotations

from app.core.capabilities.capability_registry import CapabilityRegistry
from app.core.capabilities.builtins.system_capabilities import (
    register_system_capabilities,
)


def build_capability_registry() -> CapabilityRegistry:
    """
    Tworzy i inicjalizuje CapabilityRegistry dla całego systemu.

    To jest centralny punkt:
    - zbiera wszystkie capability
    - przygotowuje registry dla Core
    """

    registry = CapabilityRegistry()

    # built-in system capabilities
    register_system_capabilities(registry)

    return registry