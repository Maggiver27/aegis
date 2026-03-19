from __future__ import annotations

from app.core.runtime.core_runtime import CoreRuntime


def bootstrap_core_runtime() -> CoreRuntime:
    """Create and start a minimal MSC-1 runtime."""
    runtime = CoreRuntime(name="mcgiver-ai-core")

    runtime.set_metadata("bootstrap_mode", "msc")
    runtime.set_metadata("component", "core_runtime")
    runtime.set_metadata("action_bus_enabled", False)

    runtime.start()
    return runtime