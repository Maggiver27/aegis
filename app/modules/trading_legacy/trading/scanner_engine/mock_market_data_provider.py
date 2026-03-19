from __future__ import annotations

from typing import Any

from app.trading.pair_universe import PAIR_UNIVERSE


class MockMarketDataProvider:
    """
    Temporary mock market data provider for development stage B.

    Purpose:
    - provide stable, repeatable input to strategy layer
    - allow MarketScanner + Strategy + RiskManager pipeline testing
    - avoid MT5 dependency at this stage
    """

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        if symbol not in PAIR_UNIVERSE:
            raise ValueError(f"Unsupported symbol for mock data: {symbol}")

        base_price = self._base_price_for_symbol(symbol)
        trend_bias = self._trend_bias_for_symbol(symbol)
        ma_fast, ma_slow = self._moving_averages_for_symbol(
            symbol=symbol,
            price=base_price,
            trend_bias=trend_bias,
        )

        return {
            "symbol": symbol,
            "timeframe": "M5",
            "price": base_price,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "trend_bias": trend_bias,
            "source": "mock_market_data_provider",
        }

    def _base_price_for_symbol(self, symbol: str) -> float:
        overrides: dict[str, float] = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2710,
            "USDJPY": 149.20,
            "GBPJPY": 189.40,
            "XAUUSD": 2165.0,
            "US30": 38950.0,
            "DJ30": 38950.0,
            "GER40": 17480.0,
            "NAS100": 18120.0,
            "USDX": 103.80,
        }

        if symbol in overrides:
            return overrides[symbol]

        # Stable deterministic fallback for remaining instruments
        numeric_seed = sum(ord(char) for char in symbol)
        return round(50.0 + (numeric_seed % 5000) / 100.0, 5)

    def _trend_bias_for_symbol(self, symbol: str) -> str:
        long_bias_symbols = {
            "DJ30",
            "GER40",
            "EURUSD",
            "GBPUSD",
            "EURJPY",
            "AUDUSD",
            "XAUUSD",
        }

        if symbol in long_bias_symbols:
            return "LONG"

        return "SHORT"

    def _moving_averages_for_symbol(
        self,
        *,
        symbol: str,
        price: float,
        trend_bias: str,
    ) -> tuple[float, float]:
        """
        Create deterministic MA relationship:
        - LONG bias -> ma_fast above ma_slow
        - SHORT bias -> ma_fast below ma_slow

        This gives strategy valid input and predictable outcomes.
        """
        pip_step = self._pip_step_for_symbol(symbol)

        if trend_bias == "LONG":
            ma_slow = round(price - (2 * pip_step), 5)
            ma_fast = round(price - pip_step, 5)
            return ma_fast, ma_slow

        ma_slow = round(price + (2 * pip_step), 5)
        ma_fast = round(price + pip_step, 5)
        return ma_fast, ma_slow

    def _pip_step_for_symbol(self, symbol: str) -> float:
        if symbol.endswith("JPY"):
            return 0.10

        if symbol in {"XAUUSD"}:
            return 1.00

        if symbol in {"DJ30", "GER40", "NAS100", "US30"}:
            return 10.0

        if symbol == "USDX":
            return 0.10

        return 0.0010
