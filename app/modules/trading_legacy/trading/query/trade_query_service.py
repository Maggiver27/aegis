from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.trading.models.trade import Trade, TradeStatus


@dataclass(slots=True)
class TradeQuery:
    status: TradeStatus | None = None
    pair: str | None = None
    strategy_name: str | None = None
    timeframe: str | None = None
    limit: int | None = None


class TradeQueryService:
    """
    Read/query layer for Trade collections.

    Purpose:
    - filter trade history without polluting repository with business filtering rules
    - keep query logic outside orchestrator
    - provide reusable filtered views for CLI, stats, reporting, future API/UI
    """

    def filter_trades(
        self,
        trades: Iterable[Trade],
        query: TradeQuery,
    ) -> list[Trade]:
        results = list(trades)

        if query.status is not None:
            results = [trade for trade in results if trade.status == query.status]

        if query.pair is not None:
            wanted_pair = query.pair.strip().upper()
            results = [
                trade for trade in results
                if trade.pair.strip().upper() == wanted_pair
            ]

        if query.strategy_name is not None:
            wanted_strategy = query.strategy_name.strip().upper()
            results = [
                trade for trade in results
                if trade.strategy_name.strip().upper() == wanted_strategy
            ]

        if query.timeframe is not None:
            wanted_timeframe = query.timeframe.strip().upper()
            results = [
                trade for trade in results
                if trade.timeframe.strip().upper() == wanted_timeframe
            ]

        if query.limit is not None:
            if query.limit <= 0:
                return []
            results = results[:query.limit]

        return results

    def parse_status(self, raw_status: str) -> TradeStatus:
        value = raw_status.strip().lower()

        for status in TradeStatus:
            if status.value == value:
                return status

        allowed = ", ".join(status.value for status in TradeStatus)
        raise ValueError(f"Unsupported status: {raw_status}. Allowed: {allowed}")

    def summarize(self, trades: Iterable[Trade]) -> dict[str, int]:
        summary: dict[str, int] = {}

        for trade in trades:
            key = trade.status.value
            summary[key] = summary.get(key, 0) + 1

        return dict(sorted(summary.items()))