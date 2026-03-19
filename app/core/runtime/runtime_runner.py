from __future__ import annotations

import sys

from app.core.runtime.runtime_bootstrap import bootstrap_core_runtime


def main() -> None:
    runtime = bootstrap_core_runtime()

    print("[MSC] Core Runtime started")

    if len(sys.argv) < 2:
        print("[MSC] No command provided")
        print("[MSC] Example: python -m app.core.runtime.runtime_runner system.ping")
        runtime.stop()
        return

    command = sys.argv[1]

    print(f"[MSC] Executing command: {command}")

    try:
        result = runtime.execute(command)
        print(f"[MSC] Result: {result}")
    except Exception as e:
        print(f"[MSC] Error: {e}")

    runtime.stop()

    print("[MSC] Core Runtime stopped")


if __name__ == "__main__":
    main()