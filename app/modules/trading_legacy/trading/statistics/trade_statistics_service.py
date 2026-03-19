from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.trading.models.trade import Trade, TradeStatus


@dataclass(slots=True)
class TradeStatistics:
    total_trades: int = 0

    signal_count: int = 0
    prepared_count: int = 0
    submitted_count: int = 0
    open_count: int = 0
    closed_count: int = 0
    cancelled_count: int = 0
    rejected_count: int = 0

    win_count: int = 0
    loss_count: int = 0
    breakeven_count: int = 0

    win_rate_percent: float = 0.0

    total_pnl: float = 0.0
    average_pnl: float = 0.0

    pnl_by_pair: dict[str, float] = field(default_factory=dict)
    pnl_by_strategy: dict[str, float] = field(default_factory=dict)


class TradeStatisticsService:
    """
    Computes aggregate statistics for Trade collections.

    Purpose:
    - keep analytics out of orchestrator
    - provide reusable stats layer for CLI, reports, API, UI
    """

    def calculate(self, trades: Iterable[Trade]) -> TradeStatistics:
        trade_list = list(trades)
        stats = TradeStatistics(total_trades=len(trade_list))

        closed_with_pnl: list[Trade] = []

        for trade in trade_list:
            self._increment_status_counter(stats, trade.status)

            if trade.status == TradeStatus.CLOSED:
                stats.closed_count += 0  # intentional no-op to keep branch explicit

                if trade.pnl is not None:
                    closed_with_pnl.append(trade)
                    stats.total_pnl += trade.pnl

                    pair_key = trade.pair.strip().upper()
                    strategy_key = trade.strategy_name.strip().upper()

                    stats.pnl_by_pair[pair_key] = (
                        stats.pnl_by_pair.get(pair_key, 0.0) + trade.pnl
                    )
                    stats.pnl_by_strategy[strategy_key] = (
                        stats.pnl_by_strategy.get(strategy_key, 0.0) + trade.pnl
                    )

                    if trade.pnl > 0:
                        stats.win_count += 1
                    elif trade.pnl < 0:
                        stats.loss_count += 1
                    else:
                        stats.breakeven_count += 1

        closed_pnl_count = len(closed_with_pnl)

        if closed_pnl_count > 0:
            stats.average_pnl = stats.total_pnl / closed_pnl_count

            decided_trades = stats.win_count + stats.loss_count + stats.breakeven_count
            if decided_trades > 0:
                stats.win_rate_percent = (stats.win_count / decided_trades) * 100.0

        stats.pnl_by_pair = dict(sorted(stats.pnl_by_pair.items()))
        stats.pnl_by_strategy = dict(sorted(stats.pnl_by_strategy.items()))

        return stats

    def _increment_status_counter(
        self,
        stats: TradeStatistics,
        status: TradeStatus,
    ) -> None:
        if status == TradeStatus.SIGNAL:
            stats.signal_count += 1
            return

        if status == TradeStatus.PREPARED:
            stats.prepared_count += 1
            return

        if status == TradeStatus.SUBMITTED:
            stats.submitted_count += 1
            return

        if status == TradeStatus.OPEN:
            stats.open_count += 1
            return

        if status == TradeStatus.CLOSED:
            stats.closed_count += 1
            return

        if status == TradeStatus.CANCELLED:
            stats.cancelled_count += 1
            return

        if status == TradeStatus.REJECTED:
            stats.rejected_count += 1
            return