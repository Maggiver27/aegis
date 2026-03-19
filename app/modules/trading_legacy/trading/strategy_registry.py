from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class StrategyProtocol(Protocol):
    name: str

    def evaluate(self, market_scan_result: Any) -> dict[str, Any] | None:
        ...


@dataclass(slots=True)
class MACrossStrategy:
    name: str = "MA_CROSS"
    stop_distance: float = 0.0020
    take_profit_distance: float = 0.0040

    def evaluate(self, market_scan_result: Any) -> dict[str, Any] | None:
        symbol = _read_value(market_scan_result, "symbol", "UNKNOWN")
        timeframe = _read_value(market_scan_result, "timeframe", "UNKNOWN")
        price = _read_float(market_scan_result, "price")
        ma_fast = _read_float(market_scan_result, "ma_fast")
        ma_slow = _read_float(market_scan_result, "ma_slow")
        trend_bias = str(_read_value(market_scan_result, "trend_bias", "")).upper()

        if price is None or ma_fast is None or ma_slow is None:
            return {
                "action": "HOLD",
                "direction": None,
                "confidence": 0.0,
                "should_trade": False,
                "reason": "Missing required MA/price values.",
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "trend_follow",
            }

        if ma_fast > ma_slow and trend_bias in {"LONG", "BUY", ""}:
            return {
                "action": "BUY",
                "direction": "LONG",
                "confidence": 0.7,
                "should_trade": True,
                "reason": "MA fast is above MA slow and bias supports long.",
                "entry": price,
                "stop_loss": round(price - self.stop_distance, 5),
                "take_profit": round(price + self.take_profit_distance, 5),
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "trend_follow",
            }

        if ma_fast < ma_slow and trend_bias in {"SHORT", "SELL", ""}:
            return {
                "action": "SELL",
                "direction": "SHORT",
                "confidence": 0.7,
                "should_trade": True,
                "reason": "MA fast is below MA slow and bias supports short.",
                "entry": price,
                "stop_loss": round(price + self.stop_distance, 5),
                "take_profit": round(price - self.take_profit_distance, 5),
                "symbol": symbol,
                "timeframe": timeframe,
                "signal_type": "trend_follow",
            }

        return {
            "action": "HOLD",
            "direction": None,
            "confidence": 0.3,
            "should_trade": False,
            "reason": "No MA cross confirmation.",
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_type": "trend_follow",
        }


class StrategyRegistry:
    """
    Strategy registry:
    - receives config from bootstrap
    - registers available strategies
    - returns active strategy selected in config
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._strategies: dict[str, StrategyProtocol] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(MACrossStrategy())

    def register(self, strategy: StrategyProtocol) -> None:
        self._strategies[strategy.name.upper()] = strategy

    def get_active_strategy_name(self) -> str:
        trading_cfg = self._config.get("trading", {})
        if isinstance(trading_cfg, dict):
            active = trading_cfg.get("active_strategy")
            if isinstance(active, str) and active.strip():
                return active.strip().upper()

        active = self._config.get("active_strategy")
        if isinstance(active, str) and active.strip():
            return active.strip().upper()

        return "MA_CROSS"

    def get_active_strategy(self) -> StrategyProtocol:
        strategy_name = self.get_active_strategy_name()

        strategy = self._strategies.get(strategy_name)
        if strategy is not None:
            return strategy

        if "MA_CROSS" in self._strategies:
            return self._strategies["MA_CROSS"]

        raise ValueError("No strategy registered in StrategyRegistry.")

    def list_strategies(self) -> list[str]:
        return sorted(self._strategies.keys())


def _read_value(obj: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _read_float(obj: Any, field_name: str) -> float | None:
    value = _read_value(obj, field_name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None