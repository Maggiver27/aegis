from __future__ import annotations

from app.core.runtime.core_runtime import CoreRuntime


def bootstrap_core_runtime() -> CoreRuntime:
    """
    Minimal Stable Core bootstrap for Core Runtime only.

    Responsibility:
    - create the runtime object
    - attach minimal runtime metadata
    - start the runtime
    - return the ready runtime instance

    This bootstrap is intentionally isolated from:
    - trading
    - legacy orchestrator
    - old application bootstrap
    """

    runtime = CoreRuntime(name="mcgiver-ai-core")

    runtime.set_metadata("bootstrap_mode", "msc")
    runtime.set_metadata("component", "core_runtime")
    runtime.set_metadata("version", "msc-step-1")

    runtime.start()

    return runtime