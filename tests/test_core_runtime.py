from app.core.runtime.core_runtime import CoreRuntime, RuntimeStatus
from app.core.runtime.runtime_bootstrap import bootstrap_core_runtime


def test_core_runtime_initial_state() -> None:
    runtime = CoreRuntime()

    snapshot = runtime.snapshot()
    assert snapshot.status == RuntimeStatus.CREATED
    assert snapshot.started_at is None
    assert snapshot.stopped_at is None


def test_core_runtime_start_and_stop_lifecycle() -> None:
    runtime = CoreRuntime()
    runtime.start()
    started_snapshot = runtime.snapshot()

    assert started_snapshot.status == RuntimeStatus.RUNNING
    assert started_snapshot.started_at is not None
    assert started_snapshot.stopped_at is None

    runtime.stop()
    stopped_snapshot = runtime.snapshot()

    assert stopped_snapshot.status == RuntimeStatus.STOPPED
    assert stopped_snapshot.started_at is not None
    assert stopped_snapshot.stopped_at is not None


def test_core_runtime_metadata_roundtrip() -> None:
    runtime = CoreRuntime()
    runtime.set_metadata("mode", "msc")

    assert runtime.get_metadata("mode") == "msc"
    assert runtime.get_metadata("missing", "default") == "default"


def test_bootstrap_core_runtime_is_minimal_and_running() -> None:
    runtime = bootstrap_core_runtime()
    snapshot = runtime.snapshot()

    assert snapshot.status == RuntimeStatus.RUNNING
    assert snapshot.metadata["bootstrap_mode"] == "msc"
    assert snapshot.metadata["action_bus_enabled"] is False
