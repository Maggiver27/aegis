import time
import threading

from app.event_bus.event_bus import EventBus
from app.core.event_factory import create_system_health_check


class SchedulerService:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.running = False

    def start(self) -> None:
        self.running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()

    def stop(self) -> None:
        self.running = False

    def _run_loop(self) -> None:
        while self.running:
            self._run_health_check()
            time.sleep(10)

    def _run_health_check(self) -> None:
        event = create_system_health_check({
            "status": "ok"
        })

        self.event_bus.publish(event)