from __future__ import annotations

from app.core.runtime.runtime_bootstrap import bootstrap_core_runtime


def main() -> None:
    runtime = bootstrap_core_runtime()
    snapshot = runtime.snapshot()

    print("[MSC] Core Runtime started")
    print(f"[MSC] Name: {snapshot.name}")
    print(f"[MSC] Status: {snapshot.status}")
    print(f"[MSC] Started at: {snapshot.started_at}")
    print(f"[MSC] Metadata: {snapshot.metadata}")

    runtime.stop()

    stopped_snapshot = runtime.snapshot()
    print("[MSC] Core Runtime stopped")
    print(f"[MSC] Status after stop: {stopped_snapshot.status}")
    print(f"[MSC] Stopped at: {stopped_snapshot.stopped_at}")


if __name__ == "__main__":
    main()