from __future__ import annotations

from app.core.runtime.runtime_bootstrap import bootstrap_core_runtime


def main() -> None:
    runtime = bootstrap_core_runtime()

    print("\n=== RUNTIME SNAPSHOT ===")
    print(runtime.snapshot())

    print("\n=== RUNTIME EXECUTION TEST PASSED ===\n")


if __name__ == "__main__":
    main()
