from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any


class CSVMarketDataProvider:
    """
    Reads MT5-exported CSV candle files and builds strategy-ready snapshots.

    Supported MT5 export format:
        <DATE>	<TIME>	<OPEN>	<HIGH>	<LOW>	<CLOSE>	<TICKVOL>	<VOL>	<SPREAD>
        2026.03.02	00:00:00	1.17718	1.17718	1.17640	1.17667	97	0	6

    Output snapshot example:
        {
            "symbol": "EURUSD",
            "timeframe": "M5",
            "price": 1.1005,
            "ma_fast": 1.1002,
            "ma_slow": 1.0998,
            "trend_bias": "LONG",
            "current_spread": 6.0,
            "average_spread": 7.1,
            "average_range": 0.00084,
            "latest_candle_time": "2026.03.02 00:00:00",
            "source": "csv_market_data_provider",
        }
    """

    def __init__(
        self,
        data_dir: str = "app/trading/data/market",
        timeframe: str = "M5",
        ma_fast_period: int = 20,
        ma_slow_period: int = 50,
        volatility_period: int = 20,
        spread_average_period: int = 20,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.timeframe = timeframe
        self.ma_fast_period = ma_fast_period
        self.ma_slow_period = ma_slow_period
        self.volatility_period = volatility_period
        self.spread_average_period = spread_average_period

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        candles = self._load_candles(symbol)

        minimum_required = max(
            self.ma_fast_period,
            self.ma_slow_period,
            self.volatility_period,
            self.spread_average_period,
        )
        if len(candles) < minimum_required:
            raise ValueError(
                f"Not enough candles for {symbol}. "
                f"Required at least {minimum_required}, got {len(candles)}."
            )

        closes = [candle["close"] for candle in candles]

        price = closes[-1]
        ma_fast = self._moving_average(closes, self.ma_fast_period)
        ma_slow = self._moving_average(closes, self.ma_slow_period)

        trend_bias = self._build_trend_bias(
            price=price,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
        )

        current_spread = candles[-1]["spread"]
        average_spread = self._average_spread(
            candles,
            self.spread_average_period,
        )
        average_range = self._average_range(
            candles,
            self.volatility_period,
        )
        latest_candle_time = candles[-1]["time"]

        return {
            "symbol": symbol,
            "timeframe": self.timeframe,
            "price": price,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "trend_bias": trend_bias,
            "current_spread": current_spread,
            "average_spread": average_spread,
            "average_range": average_range,
            "latest_candle_time": latest_candle_time,
            "source": "csv_market_data_provider",
        }

    def _load_candles(self, symbol: str) -> list[dict[str, Any]]:
        file_path = self._build_file_path(symbol)

        if not file_path.exists():
            raise FileNotFoundError(
                f"CSV file not found for {symbol}: {file_path}"
            )

        for encoding in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
            try:
                return self._read_mt5_file(file_path, encoding)
            except UnicodeError:
                continue

        raise ValueError(
            f"Could not decode CSV file for {symbol}: {file_path}"
        )

    def _read_mt5_file(
        self,
        file_path: Path,
        encoding: str,
    ) -> list[dict[str, Any]]:
        candles: list[dict[str, Any]] = []

        with file_path.open("r", encoding=encoding, newline="") as file:
            reader = csv.DictReader(file, delimiter="\t")

            required_columns = {
                "<DATE>",
                "<TIME>",
                "<OPEN>",
                "<HIGH>",
                "<LOW>",
                "<CLOSE>",
                "<TICKVOL>",
                "<SPREAD>",
            }

            if reader.fieldnames is None:
                raise ValueError(f"CSV file has no header: {file_path}")

            header = {name.strip().upper() for name in reader.fieldnames}
            if not required_columns.issubset(header):
                raise ValueError(
                    f"CSV file {file_path} does not match MT5 export format. "
                    f"Expected columns: {sorted(required_columns)}. "
                    f"Found: {reader.fieldnames}"
                )

            for row in reader:
                date_text = self._read_text(row, "<DATE>")
                time_text = self._read_text(row, "<TIME>")

                candles.append(
                    {
                        "time": f"{date_text} {time_text}",
                        "open": self._read_float(row, "<OPEN>"),
                        "high": self._read_float(row, "<HIGH>"),
                        "low": self._read_float(row, "<LOW>"),
                        "close": self._read_float(row, "<CLOSE>"),
                        "volume": self._read_float(row, "<TICKVOL>"),
                        "spread": self._read_float(row, "<SPREAD>"),
                    }
                )

        return candles

    def _build_file_path(self, symbol: str) -> Path:
        filename = f"{symbol}_{self.timeframe}.csv"
        return self.data_dir / filename

    @staticmethod
    def _moving_average(values: list[float], period: int) -> float:
        if len(values) < period:
            raise ValueError(
                f"Not enough values to calculate MA{period}. "
                f"Got {len(values)} values."
            )

        return round(mean(values[-period:]), 5)

    @staticmethod
    def _average_spread(
        candles: list[dict[str, Any]],
        period: int,
    ) -> float:
        if len(candles) < period:
            raise ValueError(
                f"Not enough candles to calculate average spread over {period}."
            )

        spreads = [float(candle["spread"]) for candle in candles[-period:]]
        return round(mean(spreads), 5)

    @staticmethod
    def _average_range(
        candles: list[dict[str, Any]],
        period: int,
    ) -> float:
        if len(candles) < period:
            raise ValueError(
                f"Not enough candles to calculate average range over {period}."
            )

        ranges = [
            float(candle["high"]) - float(candle["low"])
            for candle in candles[-period:]
        ]
        return round(mean(ranges), 5)

    @staticmethod
    def _build_trend_bias(
        *,
        price: float,
        ma_fast: float,
        ma_slow: float,
    ) -> str:
        if ma_fast > ma_slow and price >= ma_fast:
            return "LONG"

        if ma_fast < ma_slow and price <= ma_fast:
            return "SHORT"

        if ma_fast > ma_slow:
            return "LONG"

        if ma_fast < ma_slow:
            return "SHORT"

        return "NEUTRAL"

    @staticmethod
    def _read_text(row: dict[str, str], key: str) -> str:
        value = row.get(key)
        if value is None:
            raise ValueError(f"Missing column value: {key}")

        text = str(value).strip()
        if not text:
            raise ValueError(f"Empty text value in column: {key}")

        return text

    @staticmethod
    def _read_float(row: dict[str, str], key: str) -> float:
        value = row.get(key)
        if value is None:
            raise ValueError(f"Missing column value: {key}")

        text = str(value).strip()
        if not text:
            raise ValueError(f"Empty numeric value in column: {key}")

        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid numeric value in column '{key}': {text}"
            ) from exc