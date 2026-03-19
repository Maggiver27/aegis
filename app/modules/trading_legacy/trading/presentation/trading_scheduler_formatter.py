from __future__ import annotations

from app.trading.scheduler.trading_scheduler import TradingSchedulerStatus


class TradingSchedulerFormatter:
    def format(self, status: TradingSchedulerStatus) -> str:
        lines: list[str] = []

        lines.append("TRADING SCHEDULER")
        lines.append("-" * 72)
        lines.append(f"Running: {status.is_running}")
        lines.append(f"Interval seconds: {status.interval_seconds}")
        lines.append(f"Auto execute paper: {status.auto_execute_paper}")
        lines.append(f"Started at: {status.started_at or '-'}")
        lines.append(f"Last run at: {status.last_run_at or '-'}")
        lines.append(f"Run count: {status.run_count}")

        return "\n".join(lines)