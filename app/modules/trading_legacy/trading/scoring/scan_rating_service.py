from __future__ import annotations

from datetime import datetime
from typing import Any

from app.trading.models.scan_rating import ScanRating


class ScanRatingService:
    """
    Service responsible for scoring a normalized trading signal candidate.

    Architectural role:
    - input: normalized candidate (dict or object-like instance)
    - output: ScanRating domain model
    - no persistence
    - no orchestration
    - no execution logic

    ScanRating v2:
    focuses on actual trading signal quality rather than only field presence.
    """

    def __init__(self) -> None:
        self._max_score = 100.0

    def rate(self, candidate: Any) -> ScanRating:
        symbol = self._read(candidate, "symbol", "UNKNOWN")
        timeframe = self._read(candidate, "timeframe", "UNKNOWN")
        strategy_name = self._read(candidate, "strategy_name", "UNKNOWN")
        direction = self._normalize_direction(
            self._read(candidate, "direction", None)
        )
        should_trade = bool(self._read(candidate, "should_trade", False))
        confidence = self._to_float(self._read(candidate, "confidence", 0.0))
        reason = str(self._read(candidate, "reason", "") or "")

        entry = self._to_optional_float(self._read(candidate, "entry", None))
        stop_loss = self._to_optional_float(
            self._read(candidate, "stop_loss", None)
        )
        take_profit = self._to_optional_float(
            self._read(candidate, "take_profit", None)
        )

        price = self._to_optional_float(self._read(candidate, "price", None))
        ma_fast = self._to_optional_float(self._read(candidate, "ma_fast", None))
        ma_slow = self._to_optional_float(self._read(candidate, "ma_slow", None))
        trend_bias = self._normalize_direction(
            self._read(candidate, "trend_bias", None)
        )

        current_spread = self._to_optional_float(
            self._read(candidate, "current_spread", None)
        )
        average_spread = self._to_optional_float(
            self._read(candidate, "average_spread", None)
        )
        average_range = self._to_optional_float(
            self._read(candidate, "average_range", None)
        )
        latest_candle_time = self._read(candidate, "latest_candle_time", None)

        rating_factors: dict[str, float] = {}

        rating_factors["structure_quality"] = self._score_structure(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            direction=direction,
            should_trade=should_trade,
        )
        rating_factors["confidence_quality"] = self._score_confidence(confidence)
        rating_factors["trend_alignment"] = self._score_trend_alignment(
            direction=direction,
            trend_bias=trend_bias,
            price=price,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
        )
        rating_factors["volatility_fit"] = self._score_volatility_fit(
            entry=entry,
            stop_loss=stop_loss,
            average_range=average_range,
        )
        rating_factors["spread_cost"] = self._score_spread_cost(
            current_spread=current_spread,
            average_spread=average_spread,
        )
        rating_factors["session_quality"] = self._score_session_quality(
            latest_candle_time=latest_candle_time,
        )
        rating_factors["reason_quality"] = self._score_reason(reason)
        rating_factors["rr_quality"] = self._score_rr(
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        raw_score = sum(rating_factors.values())
        bounded_score = max(0.0, min(raw_score, self._max_score))

        return ScanRating(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            direction=direction,
            score=bounded_score,
            max_score=self._max_score,
            rating_factors=rating_factors,
            metadata={
                "should_trade": should_trade,
                "confidence": confidence,
                "reason": reason,
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "price": price,
                "ma_fast": ma_fast,
                "ma_slow": ma_slow,
                "trend_bias": trend_bias,
                "current_spread": current_spread,
                "average_spread": average_spread,
                "average_range": average_range,
                "latest_candle_time": latest_candle_time,
                "source_type": type(candidate).__name__,
            },
        )

    def _read(self, candidate: Any, field_name: str, default: Any) -> Any:
        if isinstance(candidate, dict):
            return candidate.get(field_name, default)
        return getattr(candidate, field_name, default)

    def _normalize_direction(self, value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip().upper()
        if text in {"BUY", "LONG"}:
            return "LONG"
        if text in {"SELL", "SHORT"}:
            return "SHORT"
        return None

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_optional_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _score_structure(
        self,
        *,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        direction: str | None,
        should_trade: bool,
    ) -> float:
        """
        Structure quality range: 0 - 10

        Small sanity-check bucket.
        This is intentionally no longer the main driver of score.
        """
        score = 0.0

        if symbol and symbol != "UNKNOWN":
            score += 2.0
        if timeframe and timeframe != "UNKNOWN":
            score += 2.0
        if strategy_name and strategy_name != "UNKNOWN":
            score += 2.0
        if direction in {"LONG", "SHORT"}:
            score += 2.0
        if should_trade:
            score += 2.0

        return score

    def _score_confidence(self, confidence: float) -> float:
        """
        Confidence score range: 0 - 15

        Supported practical formats:
        - 0.0 to 1.0
        - 0 to 100
        """
        if confidence <= 0:
            return 0.0

        normalized = confidence
        if confidence > 1.0:
            normalized = confidence / 100.0

        normalized = max(0.0, min(normalized, 1.0))
        return round(normalized * 15.0, 2)

    def _score_trend_alignment(
        self,
        *,
        direction: str | None,
        trend_bias: str | None,
        price: float | None,
        ma_fast: float | None,
        ma_slow: float | None,
    ) -> float:
        """
        Trend alignment range: 0 - 20
        """
        if direction not in {"LONG", "SHORT"}:
            return 0.0

        if trend_bias is None or price is None or ma_fast is None or ma_slow is None:
            return 0.0

        score = 0.0

        if direction == trend_bias:
            score += 10.0

        if direction == "LONG" and ma_fast > ma_slow:
            score += 5.0
        elif direction == "SHORT" and ma_fast < ma_slow:
            score += 5.0

        if direction == "LONG" and price >= ma_fast:
            score += 5.0
        elif direction == "SHORT" and price <= ma_fast:
            score += 5.0

        return score

    def _score_volatility_fit(
        self,
        *,
        entry: float | None,
        stop_loss: float | None,
        average_range: float | None,
    ) -> float:
        """
        Volatility fit range: 0 - 15

        Compares stop distance to recent average candle range.
        """
        if entry is None or stop_loss is None or average_range is None:
            return 0.0

        if average_range <= 0:
            return 0.0

        stop_distance = abs(entry - stop_loss)
        ratio = stop_distance / average_range

        if ratio < 0.25:
            return 3.0
        if ratio < 0.50:
            return 8.0
        if ratio <= 1.50:
            return 15.0
        if ratio <= 2.50:
            return 9.0
        return 4.0

    def _score_spread_cost(
        self,
        *,
        current_spread: float | None,
        average_spread: float | None,
    ) -> float:
        """
        Spread cost range: 0 - 10

        Rewards candidates when current spread is normal or better than normal.
        """
        if current_spread is None or average_spread is None:
            return 0.0

        if current_spread < 0 or average_spread <= 0:
            return 0.0

        ratio = current_spread / average_spread

        if ratio <= 0.80:
            return 10.0
        if ratio <= 1.00:
            return 8.0
        if ratio <= 1.20:
            return 6.0
        if ratio <= 1.50:
            return 3.0
        return 0.0

    def _score_session_quality(self, *, latest_candle_time: Any) -> float:
        """
        Session quality range: 0 - 10

        Uses candle hour as a lightweight proxy.
        High-liquidity London/NY overlap gets highest score.
        """
        hour = self._extract_hour(latest_candle_time)
        if hour is None:
            return 0.0

        if 13 <= hour <= 16:
            return 10.0
        if 7 <= hour <= 12:
            return 8.0
        if 17 <= hour <= 20:
            return 5.0
        return 2.0

    def _extract_hour(self, value: Any) -> int | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).hour
            except ValueError:
                continue

        return None

    def _score_reason(self, reason: str) -> float:
        """
        Reason quality range: 0 - 5
        """
        cleaned = reason.strip()
        if not cleaned:
            return 0.0
        if len(cleaned) < 10:
            return 2.0
        return 5.0

    def _score_rr(
        self,
        *,
        direction: str | None,
        entry: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> float:
        """
        Risk/reward quality range: 0 - 15
        """
        if direction not in {"LONG", "SHORT"}:
            return 0.0

        if entry is None or stop_loss is None or take_profit is None:
            return 0.0

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)

        if risk <= 0 or reward <= 0:
            return 0.0

        rr = reward / risk

        if rr < 1.0:
            return 2.0
        if rr < 1.5:
            return 6.0
        if rr < 2.0:
            return 10.0
        if rr < 3.0:
            return 13.0
        return 15.0