from __future__ import annotations

from typing import Any

from app.trading.models.trade import Trade


class RiskManager:
    """
    Converts a normalized strategy / rule-engine decision into a Trade object.

    This version includes explicit validation and detailed rejection reasons so the
    orchestrator can log exactly why a candidate was rejected.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

        self.account_balance = float(self.config.get("account_balance", 10_000.0))
        self.account_currency = str(self.config.get("account_currency", "USD"))
        self.default_risk_percent = float(self.config.get("risk_percent", 1.0))
        self.min_lot = float(self.config.get("min_lot", 0.01))
        self.max_lot = float(self.config.get("max_lot", 100.0))
        self.lot_step = float(self.config.get("lot_step", 0.01))
        self.symbol_specs = self.config.get("symbol_specs", {})

        self._last_rejection_reason: str | None = None

    @property
    def last_rejection_reason(self) -> str | None:
        return self._last_rejection_reason

    def prepare_trade(self, signal: Any) -> Trade | None:
        """
        Build Trade from signal-like input.

        Returns:
            Trade if valid, otherwise None.

        Rejection reason is stored in self.last_rejection_reason.
        """
        self._last_rejection_reason = None

        try:
            data = self._normalize_signal(signal)
            self._validate_signal_data(data)

            pair = data["symbol"]
            direction = data["direction"]
            timeframe = data["timeframe"]
            strategy_name = data["strategy_name"]
            signal_type = data["signal_type"]
            source = data["source"]

            entry = float(data["entry"])
            stop_loss = float(data["stop_loss"])
            take_profit = float(data["take_profit"])
            risk_percent = float(data["risk_percent"])
            confidence = float(data["confidence"])
            risk_reward = float(data["risk_reward"])

            scan_score = self._to_float_or_none(data.get("scan_score"))
            scan_score_ratio = self._to_float_or_none(data.get("scan_score_ratio"))
            scan_rating_factors = self._normalize_scan_rating_factors(
                data.get("scan_rating_factors")
            )

            stop_distance_price = abs(entry - stop_loss)
            if stop_distance_price <= 0:
                raise ValueError("stop distance price must be > 0")

            pip_size = self._get_pip_size(pair)
            if pip_size <= 0:
                raise ValueError("pip_size must be > 0")

            stop_distance_pips = stop_distance_price / pip_size
            if stop_distance_pips <= 0:
                raise ValueError("stop_distance_pips must be > 0")

            pip_value_per_standard_lot = self._get_pip_value_per_standard_lot(pair)
            if pip_value_per_standard_lot <= 0:
                raise ValueError("pip_value_per_standard_lot must be > 0")

            risk_amount = self.account_balance * (risk_percent / 100.0)
            if risk_amount <= 0:
                raise ValueError("risk_amount must be > 0")

            raw_lot = risk_amount / (stop_distance_pips * pip_value_per_standard_lot)
            lot_size = self._normalize_lot(raw_lot)
            if lot_size <= 0:
                raise ValueError("lot_size must be > 0 after normalization")

            metadata = {
                "symbol": pair,
                "timeframe": timeframe,
                "signal_type": signal_type,
                "quality_gate_passed": bool(data.get("quality_gate_passed", True)),
                "risk_reward": risk_reward,
                "confidence": confidence,
                "min_confidence_threshold": float(
                    data.get("min_confidence_threshold", 0.0)
                ),
                "min_risk_reward_threshold": float(
                    data.get("min_risk_reward_threshold", 0.0)
                ),
            }

            trade = Trade(
                pair=pair,
                direction=direction,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot_size=lot_size,
                risk_percent=risk_percent,
                risk_amount=risk_amount,
                stop_distance_price=stop_distance_price,
                stop_distance_pips=stop_distance_pips,
                strategy_name=strategy_name,
                timeframe=timeframe,
                signal_type=signal_type,
                source=source,
                created_at=self._utc_now(),
                sizing_mode=self._get_sizing_mode(pair),
                pip_size=pip_size,
                pip_value_per_standard_lot=pip_value_per_standard_lot,
                scan_score=scan_score,
                scan_score_ratio=scan_score_ratio,
                scan_rating_factors=scan_rating_factors,
                metadata=metadata,
            )

            return trade

        except Exception as exc:
            self._last_rejection_reason = str(exc)
            return None

    def _normalize_signal(self, signal: Any) -> dict[str, Any]:
        """
        Accept dict or object-like signal and normalize to a plain dict.
        """
        if signal is None:
            raise ValueError("signal is None")

        if isinstance(signal, dict):
            return {
                "symbol": signal.get("symbol"),
                "direction": signal.get("direction") or signal.get("action"),
                "entry": signal.get("entry"),
                "stop_loss": signal.get("stop_loss"),
                "take_profit": signal.get("take_profit"),
                "strategy_name": signal.get("strategy_name", "UNKNOWN"),
                "timeframe": signal.get("timeframe", "UNKNOWN"),
                "signal_type": signal.get("signal_type", "UNKNOWN"),
                "source": signal.get("source", "risk_manager"),
                "risk_percent": signal.get(
                    "risk_percent",
                    self.default_risk_percent,
                ),
                "confidence": signal.get("confidence", 0.0),
                "risk_reward": signal.get("risk_reward", 0.0),
                "quality_gate_passed": signal.get("quality_gate_passed", True),
                "min_confidence_threshold": signal.get(
                    "min_confidence_threshold",
                    0.0,
                ),
                "min_risk_reward_threshold": signal.get(
                    "min_risk_reward_threshold",
                    0.0,
                ),
                "scan_score": signal.get("scan_score"),
                "scan_score_ratio": signal.get("scan_score_ratio"),
                "scan_rating_factors": signal.get("scan_rating_factors", {}),
            }

        return {
            "symbol": getattr(signal, "symbol", None),
            "direction": getattr(signal, "direction", None)
            or getattr(signal, "action", None),
            "entry": getattr(signal, "entry", None),
            "stop_loss": getattr(signal, "stop_loss", None),
            "take_profit": getattr(signal, "take_profit", None),
            "strategy_name": getattr(signal, "strategy_name", "UNKNOWN"),
            "timeframe": getattr(signal, "timeframe", "UNKNOWN"),
            "signal_type": getattr(signal, "signal_type", "UNKNOWN"),
            "source": getattr(signal, "source", "risk_manager"),
            "risk_percent": getattr(
                signal,
                "risk_percent",
                self.default_risk_percent,
            ),
            "confidence": getattr(signal, "confidence", 0.0),
            "risk_reward": getattr(signal, "risk_reward", 0.0),
            "quality_gate_passed": getattr(signal, "quality_gate_passed", True),
            "min_confidence_threshold": getattr(
                signal,
                "min_confidence_threshold",
                0.0,
            ),
            "min_risk_reward_threshold": getattr(
                signal,
                "min_risk_reward_threshold",
                0.0,
            ),
            "scan_score": getattr(signal, "scan_score", None),
            "scan_score_ratio": getattr(signal, "scan_score_ratio", None),
            "scan_rating_factors": getattr(signal, "scan_rating_factors", {}),
        }

    def _validate_signal_data(self, data: dict[str, Any]) -> None:
        symbol = self._clean_text(data.get("symbol"))
        if not symbol:
            raise ValueError("symbol is missing")

        direction_raw = self._clean_text(data.get("direction"))
        if not direction_raw:
            raise ValueError("direction is missing")

        direction = direction_raw.upper()
        if direction in {"BUY", "LONG"}:
            direction = "LONG"
        elif direction in {"SELL", "SHORT"}:
            direction = "SHORT"
        else:
            raise ValueError(
                f"direction must be LONG/SHORT or BUY/SELL, got: {direction_raw}"
            )

        entry = self._to_float(data.get("entry"), "entry")
        stop_loss = self._to_float(data.get("stop_loss"), "stop_loss")
        take_profit = self._to_float(data.get("take_profit"), "take_profit")
        risk_percent = self._to_float(data.get("risk_percent"), "risk_percent")
        confidence = self._to_float(data.get("confidence"), "confidence")
        risk_reward = self._to_float(data.get("risk_reward"), "risk_reward")

        strategy_name = self._clean_text(data.get("strategy_name")) or "UNKNOWN"
        timeframe = self._clean_text(data.get("timeframe")) or "UNKNOWN"
        signal_type = self._clean_text(data.get("signal_type")) or "UNKNOWN"
        source = self._clean_text(data.get("source")) or "risk_manager"

        if entry <= 0:
            raise ValueError("entry must be > 0")
        if stop_loss <= 0:
            raise ValueError("stop_loss must be > 0")
        if take_profit <= 0:
            raise ValueError("take_profit must be > 0")
        if risk_percent <= 0:
            raise ValueError("risk_percent must be > 0")

        if direction == "LONG":
            if not (stop_loss < entry < take_profit):
                raise ValueError(
                    "LONG setup must satisfy: stop_loss < entry < take_profit"
                )

        if direction == "SHORT":
            if not (take_profit < entry < stop_loss):
                raise ValueError(
                    "SHORT setup must satisfy: take_profit < entry < stop_loss"
                )

        data["symbol"] = symbol
        data["direction"] = direction
        data["entry"] = entry
        data["stop_loss"] = stop_loss
        data["take_profit"] = take_profit
        data["risk_percent"] = risk_percent
        data["confidence"] = confidence
        data["risk_reward"] = risk_reward
        data["strategy_name"] = strategy_name
        data["timeframe"] = timeframe
        data["signal_type"] = signal_type
        data["source"] = source

    def _normalize_scan_rating_factors(
        self,
        value: Any,
    ) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}

        normalized: dict[str, float] = {}

        for key, item in value.items():
            key_text = self._clean_text(key)
            if not key_text:
                continue

            numeric_value = self._to_float_or_none(item)
            if numeric_value is None:
                continue

            normalized[key_text] = numeric_value

        return normalized

    def _get_pip_size(self, symbol: str) -> float:
        specs = self.symbol_specs.get(symbol, {})

        if "pip_size" in specs:
            return float(specs["pip_size"])

        if symbol.endswith("JPY"):
            return 0.01

        return 0.0001

    def _get_pip_value_per_standard_lot(self, symbol: str) -> float:
        specs = self.symbol_specs.get(symbol, {})

        if "pip_value_per_standard_lot" in specs:
            return float(specs["pip_value_per_standard_lot"])

        return 10.0

    def _get_sizing_mode(self, symbol: str) -> str:
        if symbol.endswith("JPY"):
            return "jpy_quote_formula"
        return "fx_default_formula"

    def _normalize_lot(self, lot_size: float) -> float:
        if lot_size <= 0:
            return 0.0

        stepped = round(lot_size / self.lot_step) * self.lot_step
        normalized = max(self.min_lot, min(stepped, self.max_lot))
        return round(normalized, 2)

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _to_float(value: Any, field_name: str) -> float:
        if value is None:
            raise ValueError(f"{field_name} is missing")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a number, got: {value}") from exc

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _utc_now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()