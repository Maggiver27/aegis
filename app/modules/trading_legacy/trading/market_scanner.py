from __future__ import annotations

from typing import Any

from app.trading.pair_universe import PAIR_UNIVERSE
from app.trading.scanner_engine.csv_market_data_provider import (
    CSVMarketDataProvider,
)


class MarketScanner:
    """
    Market scanner using a CSV market data provider.

    Stage B architecture:
    PAIR_UNIVERSE
        ↓
    CSVMarketDataProvider
        ↓
    Strategy
        ↓
    normalized signal
        ↓
    ordered candidate list
    """

    def __init__(self, event_bus, strategy_registry) -> None:
        self.event_bus = event_bus
        self.strategy_registry = strategy_registry
        self.market_data_provider = CSVMarketDataProvider()

    def scan(self) -> list[dict[str, Any]]:
        strategy = self.strategy_registry.get_active_strategy()
        results: list[dict[str, Any]] = []

        for symbol in PAIR_UNIVERSE:
            market_data = self.market_data_provider.get_snapshot(symbol)

            raw_result = strategy.evaluate(market_data)

            normalized = self._normalize_strategy_result(
                symbol=symbol,
                market_data=market_data,
                raw_result=raw_result,
                strategy_name=getattr(strategy, "name", "UNKNOWN"),
            )

            if normalized is None:
                continue

            if not self._is_tradable_candidate(normalized):
                continue

            results.append(normalized)

        return self._order_candidates(results)

    def _normalize_strategy_result(
        self,
        *,
        symbol: str,
        market_data: dict[str, Any],
        raw_result: Any,
        strategy_name: str,
    ) -> dict[str, Any] | None:
        if raw_result is None:
            return None

        if isinstance(raw_result, dict):
            data = dict(raw_result)
        else:
            data = self._object_to_dict(raw_result)

        return {
            "symbol": data.get("symbol", symbol),
            "timeframe": data.get("timeframe", market_data.get("timeframe", "M5")),
            "direction": data.get("direction"),
            "entry": data.get("entry"),
            "stop_loss": data.get("stop_loss"),
            "take_profit": data.get("take_profit"),
            "strategy_name": data.get("strategy_name", strategy_name),
            "signal_type": data.get("signal_type", "trend_follow"),
            "confidence": self._to_float(data.get("confidence"), default=0.0),
            "risk_reward": self._to_float(data.get("risk_reward"), default=0.0),
            "should_trade": data.get("should_trade"),
            "reason": data.get("reason"),
            "price": self._to_optional_float(market_data.get("price")),
            "ma_fast": self._to_optional_float(market_data.get("ma_fast")),
            "ma_slow": self._to_optional_float(market_data.get("ma_slow")),
            "trend_bias": market_data.get("trend_bias"),
            "current_spread": self._to_optional_float(
                market_data.get("current_spread")
            ),
            "average_spread": self._to_optional_float(
                market_data.get("average_spread")
            ),
            "average_range": self._to_optional_float(
                market_data.get("average_range")
            ),
            "latest_candle_time": market_data.get("latest_candle_time"),
            "source": market_data.get("source", "unknown"),
        }

    def _is_tradable_candidate(self, data: dict[str, Any]) -> bool:
        if data.get("should_trade") is False:
            return False

        if data.get("direction") is None:
            return False

        return True

    def _order_candidates(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda item: (
                -self._to_float(item.get("confidence"), default=0.0),
                str(item.get("symbol", "")).upper(),
            ),
        )

    @staticmethod
    def _object_to_dict(obj: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}

        candidate_keys = [
            "symbol",
            "timeframe",
            "direction",
            "entry",
            "stop_loss",
            "take_profit",
            "strategy_name",
            "signal_type",
            "confidence",
            "risk_reward",
            "should_trade",
            "reason",
        ]

        for key in candidate_keys:
            if hasattr(obj, key):
                result[key] = getattr(obj, key)

        return result

    @staticmethod
    def _to_float(value: Any, *, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None