from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(slots=True)
class TradingSchedulerStatus:
    is_running: bool
    interval_seconds: int
    auto_execute_paper: bool
    started_at: str | None = None
    last_run_at: str | None = None
    run_count: int = 0


class TradingScheduler:
    """
    Simple in-process trading scheduler.

    Purpose:
    - periodically trigger market scan
    - optionally trigger paper execution for newly prepared trades
    - keep scheduling logic out of orchestrator

    Important:
    - this is local, in-process scheduling
    - it is intentionally simple at this stage
    - MT5 is NOT used here
    """

    def __init__(
        self,
        *,
        scan_callback: Callable[[], None],
        paper_execute_callback: Callable[[], None],
    ) -> None:
        self._scan_callback = scan_callback
        self._paper_execute_callback = paper_execute_callback

        self._is_running = False
        self._interval_seconds = 60
        self._auto_execute_paper = False

        self._started_at: str | None = None
        self._last_run_at: str | None = None
        self._run_count = 0

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(
        self,
        *,
        interval_seconds: int,
        auto_execute_paper: bool = False,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        if self._is_running:
            raise ValueError("Trading scheduler is already running.")

        self._interval_seconds = interval_seconds
        self._auto_execute_paper = auto_execute_paper
        self._started_at = self._utc_now()
        self._last_run_at = None
        self._run_count = 0

        self._stop_event.clear()
        self._is_running = True

        self._thread = threading.Thread(
            target=self._run_loop,
            name="TradingSchedulerThread",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if not self._is_running:
            return

        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        self._thread = None
        self._is_running = False

    def run_once(self) -> None:
        self._execute_cycle()

    def get_status(self) -> TradingSchedulerStatus:
        return TradingSchedulerStatus(
            is_running=self._is_running,
            interval_seconds=self._interval_seconds,
            auto_execute_paper=self._auto_execute_paper,
            started_at=self._started_at,
            last_run_at=self._last_run_at,
            run_count=self._run_count,
        )

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._execute_cycle()

            if self._stop_event.wait(self._interval_seconds):
                break

        self._is_running = False

    def _execute_cycle(self) -> None:
        self._last_run_at = self._utc_now()
        self._run_count += 1

        self._scan_callback()

        if self._auto_execute_paper:
            self._paper_execute_callback()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()