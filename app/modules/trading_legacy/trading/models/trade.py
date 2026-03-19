from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TradeStatus(str, Enum):
    """Enumerated statuses for the lifecycle of a trade."""

    SIGNAL = "signal"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(slots=True)
class Trade:
    """
    Domain model representing a trade together with sizing and lifecycle metadata.

    Architectural rule:
    - Trade is a data model
    - lifecycle transitions are controlled by TradeLifecycleService
    - this model should not enforce or mutate lifecycle transitions by itself
    """

    pair: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_percent: float
    risk_amount: float
    stop_distance_price: float
    stop_distance_pips: float
    strategy_name: str
    timeframe: str
    signal_type: str
    source: str
    created_at: str
    sizing_mode: str
    pip_size: float
    pip_value_per_standard_lot: float | None

    scan_score: float | None = None
    scan_score_ratio: float | None = None
    scan_rating_factors: dict[str, float] = field(default_factory=dict)

    status: TradeStatus = TradeStatus.PREPARED
    trade_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    opened_at: str | None = None
    closed_at: str | None = None
    exit_price: float | None = None
    pnl: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize this trade to a dictionary.

        Rules:
        - status is serialized as string value
        - trade_id is mapped to id for persistence boundary
        - trade_id field itself is omitted from output
        """
        data = asdict(self)
        data["status"] = self.status.value

        trade_id = data.pop("trade_id", None)
        if trade_id is not None and str(trade_id).strip():
            data["id"] = str(trade_id).strip()

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trade:
        """
        Create a Trade instance from a dictionary.

        Mapping rules:
        - id or trade_id are accepted as identifier input
        - status strings are converted to TradeStatus
        - non-dict metadata falls back to {}
        - non-dict scan_rating_factors falls back to {}
        """
        status = cls._parse_status(data.get("status", TradeStatus.PREPARED.value))

        ident = data.get("trade_id")
        if ident is None:
            ident = data.get("id")
        trade_id = cls._to_str_or_none(ident)

        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        scan_rating_factors = data.get("scan_rating_factors", {})
        if not isinstance(scan_rating_factors, dict):
            scan_rating_factors = {}

        normalized_scan_rating_factors: dict[str, float] = {}
        for key, value in scan_rating_factors.items():
            key_text = cls._to_str(key, default="")
            if not key_text:
                continue

            numeric_value = cls._to_float_or_none(value)
            if numeric_value is None:
                continue

            normalized_scan_rating_factors[key_text] = numeric_value

        return cls(
            pair=cls._to_str(data.get("pair"), default="UNKNOWN"),
            direction=cls._to_str(data.get("direction"), default="UNKNOWN"),
            entry=cls._to_float(data.get("entry"), default=0.0),
            stop_loss=cls._to_float(data.get("stop_loss"), default=0.0),
            take_profit=cls._to_float(data.get("take_profit"), default=0.0),
            lot_size=cls._to_float(data.get("lot_size"), default=0.0),
            risk_percent=cls._to_float(data.get("risk_percent"), default=0.0),
            risk_amount=cls._to_float(data.get("risk_amount"), default=0.0),
            stop_distance_price=cls._to_float(
                data.get("stop_distance_price"),
                default=0.0,
            ),
            stop_distance_pips=cls._to_float(
                data.get("stop_distance_pips"),
                default=0.0,
            ),
            strategy_name=cls._to_str(data.get("strategy_name"), default="UNKNOWN"),
            timeframe=cls._to_str(data.get("timeframe"), default="UNKNOWN"),
            signal_type=cls._to_str(data.get("signal_type"), default="UNKNOWN"),
            source=cls._to_str(data.get("source"), default="UNKNOWN"),
            created_at=cls._to_str(data.get("created_at"), default=cls._utc_now()),
            sizing_mode=cls._to_str(data.get("sizing_mode"), default="unknown"),
            pip_size=cls._to_float(data.get("pip_size"), default=0.0),
            pip_value_per_standard_lot=cls._to_float_or_none(
                data.get("pip_value_per_standard_lot")
            ),
            scan_score=cls._to_float_or_none(data.get("scan_score")),
            scan_score_ratio=cls._to_float_or_none(data.get("scan_score_ratio")),
            scan_rating_factors=normalized_scan_rating_factors,
            status=status,
            trade_id=trade_id,
            metadata=metadata,
            opened_at=cls._to_str_or_none(data.get("opened_at")),
            closed_at=cls._to_str_or_none(data.get("closed_at")),
            exit_price=cls._to_float_or_none(data.get("exit_price")),
            pnl=cls._to_float_or_none(data.get("pnl")),
        )

    @staticmethod
    def _parse_status(value: Any) -> TradeStatus:
        if isinstance(value, TradeStatus):
            return value

        text = str(value).strip().lower()
        for status in TradeStatus:
            if status.value == text:
                return status

        return TradeStatus.PREPARED

    @staticmethod
    def _to_float(value: Any, *, default: float) -> float:
        parsed = Trade._to_float_or_none(value)
        return default if parsed is None else parsed

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_str(value: Any, *, default: str) -> str:
        if value is None:
            return default

        text = str(value).strip()
        return text if text else default

    @staticmethod
    def _to_str_or_none(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()