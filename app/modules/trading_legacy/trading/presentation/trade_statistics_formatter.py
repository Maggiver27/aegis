from __future__ import annotations

from app.trading.statistics.trade_statistics_service import TradeStatistics


class TradeStatisticsFormatter:
    """
    Formats TradeStatistics into readable terminal output.
    """

    def format(self, stats: TradeStatistics) -> str:
        lines: list[str] = []

        lines.append("TRADE STATISTICS")
        lines.append("-" * 72)

        lines.append(f"Total trades: {stats.total_trades}")
        lines.append(f"Signal: {stats.signal_count}")
        lines.append(f"Prepared: {stats.prepared_count}")
        lines.append(f"Submitted: {stats.submitted_count}")
        lines.append(f"Open: {stats.open_count}")
        lines.append(f"Closed: {stats.closed_count}")
        lines.append(f"Cancelled: {stats.cancelled_count}")
        lines.append(f"Rejected: {stats.rejected_count}")

        lines.append("-" * 72)

        lines.append(f"Wins: {stats.win_count}")
        lines.append(f"Losses: {stats.loss_count}")
        lines.append(f"Breakeven: {stats.breakeven_count}")
        lines.append(f"Win rate: {stats.win_rate_percent:.2f}%")

        lines.append("-" * 72)

        lines.append(f"Total PnL: {stats.total_pnl:.2f}")
        lines.append(f"Average PnL: {stats.average_pnl:.2f}")

        lines.append("-" * 72)
        lines.append("PnL by pair:")

        if stats.pnl_by_pair:
            for pair, pnl in stats.pnl_by_pair.items():
                lines.append(f"  {pair}: {pnl:.2f}")
        else:
            lines.append("  -")

        lines.append("-" * 72)
        lines.append("PnL by strategy:")

        if stats.pnl_by_strategy:
            for strategy, pnl in stats.pnl_by_strategy.items():
                lines.append(f"  {strategy}: {pnl:.2f}")
        else:
            lines.append("  -")

        return "\n".join(lines)