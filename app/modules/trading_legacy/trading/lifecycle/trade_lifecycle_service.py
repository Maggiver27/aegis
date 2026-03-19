from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Iterable

from app.trading.models.trade import Trade, TradeStatus


class TradeLifecycleError(Exception):
    """Base exception for trade lifecycle errors."""


class InvalidTradeTransitionError(TradeLifecycleError):
    """Raised when an invalid status transition is attempted."""


class TradeValidationError(TradeLifecycleError):
    """Raised when required trade data is missing or invalid."""


class TradeLifecycleService:
    """
    Central lifecycle controller for Trade objects.

    This class is the single source of truth for valid trade status transitions.
    It prevents illegal jumps such as:
    - PREPARED -> CLOSED
    - CLOSED -> OPEN
    - OPEN -> PREPARED

    Allowed transitions:
    - PREPARED -> SUBMITTED
    - PREPARED -> CANCELLED
    - PREPARED -> REJECTED
    - SUBMITTED -> OPEN
    - SUBMITTED -> REJECTED
    - SUBMITTED -> CANCELLED
    - OPEN -> CLOSED
    """

    _ALLOWED_TRANSITIONS: dict[TradeStatus, set[TradeStatus]] = {
        TradeStatus.PREPARED: {
            TradeStatus.SUBMITTED,
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
        },
        TradeStatus.SUBMITTED: {
            TradeStatus.OPEN,
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
        },
        TradeStatus.OPEN: {
            TradeStatus.CLOSED,
        },
        TradeStatus.CLOSED: set(),
        TradeStatus.REJECTED: set(),
        TradeStatus.CANCELLED: set(),
    }

    def get_allowed_transitions(self, status: TradeStatus) -> set[TradeStatus]:
        return self._ALLOWED_TRANSITIONS.get(status, set()).copy()

    def can_transition(self, current: TradeStatus, target: TradeStatus) -> bool:
        return target in self._ALLOWED_TRANSITIONS.get(current, set())

    def ensure_transition_allowed(
        self,
        current: TradeStatus,
        target: TradeStatus,
    ) -> None:
        if self.can_transition(current, target):
            return

        allowed = ", ".join(
            sorted(
                next_status.value
                for next_status in self.get_allowed_transitions(current)
            )
        )
        raise InvalidTradeTransitionError(
            f"Invalid trade transition: {current.value} -> {target.value}. "
            f"Allowed: [{allowed}]"
        )

    def mark_submitted(self, trade: Trade) -> Trade:
        """
        PREPARED -> SUBMITTED
        """
        self.ensure_transition_allowed(trade.status, TradeStatus.SUBMITTED)
        self._validate_trade_before_submit(trade)

        return replace(
            trade,
            status=TradeStatus.SUBMITTED,
        )

    def mark_open(
        self,
        trade: Trade,
        *,
        opened_at: str | None = None,
    ) -> Trade:
        """
        SUBMITTED -> OPEN
        """
        self.ensure_transition_allowed(trade.status, TradeStatus.OPEN)

        return replace(
            trade,
            status=TradeStatus.OPEN,
            opened_at=opened_at or self._utc_now_iso(),
        )

    def mark_closed(
        self,
        trade: Trade,
        *,
        exit_price: float,
        pnl: float,
        closed_at: str | None = None,
    ) -> Trade:
        """
        OPEN -> CLOSED
        """
        self.ensure_transition_allowed(trade.status, TradeStatus.CLOSED)

        if exit_price <= 0:
            raise TradeValidationError("exit_price must be > 0 when closing a trade.")

        return replace(
            trade,
            status=TradeStatus.CLOSED,
            exit_price=exit_price,
            pnl=pnl,
            closed_at=closed_at or self._utc_now_iso(),
        )

    def mark_rejected(
        self,
        trade: Trade,
        *,
        reason: str,
    ) -> Trade:
        """
        PREPARED/SUBMITTED -> REJECTED
        """
        self.ensure_transition_allowed(trade.status, TradeStatus.REJECTED)

        clean_reason = reason.strip()
        if not clean_reason:
            raise TradeValidationError("reason is required when rejecting a trade.")

        metadata = dict(trade.metadata)
        metadata["rejection_reason"] = clean_reason
        metadata["rejected_at"] = self._utc_now_iso()

        return replace(
            trade,
            status=TradeStatus.REJECTED,
            metadata=metadata,
        )

    def mark_cancelled(
        self,
        trade: Trade,
        *,
        reason: str,
    ) -> Trade:
        """
        PREPARED/SUBMITTED -> CANCELLED
        """
        self.ensure_transition_allowed(trade.status, TradeStatus.CANCELLED)

        clean_reason = reason.strip()
        if not clean_reason:
            raise TradeValidationError("reason is required when cancelling a trade.")

        metadata = dict(trade.metadata)
        metadata["cancel_reason"] = clean_reason
        metadata["cancelled_at"] = self._utc_now_iso()

        return replace(
            trade,
            status=TradeStatus.CANCELLED,
            metadata=metadata,
        )

    def is_terminal_status(self, status: TradeStatus) -> bool:
        return status in {
            TradeStatus.CLOSED,
            TradeStatus.REJECTED,
            TradeStatus.CANCELLED,
        }

    def validate_trade(self, trade: Trade) -> None:
        """
        Full structural validation.
        Useful for debugging, tests, repository writes, and command handlers.
        """
        self._validate_core_trade_fields(trade)
        self._validate_status_specific_fields(trade)

    def validate_many(self, trades: Iterable[Trade]) -> None:
        for trade in trades:
            self.validate_trade(trade)

    def _validate_trade_before_submit(self, trade: Trade) -> None:
        self._validate_core_trade_fields(trade)

        if trade.status != TradeStatus.PREPARED:
            raise TradeValidationError(
                f"Trade must be in PREPARED status before submit, got: {trade.status.value}"
            )

    def _validate_core_trade_fields(self, trade: Trade) -> None:
        if not (trade.trade_id and trade.trade_id.strip()):
            raise TradeValidationError("trade_id is required.")

        if not trade.pair.strip():
            raise TradeValidationError("pair is required.")

        if trade.direction not in {"LONG", "SHORT"}:
            raise TradeValidationError(
                f"direction must be LONG or SHORT, got: {trade.direction}"
            )

        if trade.entry <= 0:
            raise TradeValidationError("entry must be > 0.")

        if trade.stop_loss <= 0:
            raise TradeValidationError("stop_loss must be > 0.")

        if trade.take_profit <= 0:
            raise TradeValidationError("take_profit must be > 0.")

        if trade.lot_size <= 0:
            raise TradeValidationError("lot_size must be > 0.")

        if trade.risk_percent <= 0:
            raise TradeValidationError("risk_percent must be > 0.")

        if trade.risk_amount <= 0:
            raise TradeValidationError("risk_amount must be > 0.")

        if trade.stop_distance_price <= 0:
            raise TradeValidationError("stop_distance_price must be > 0.")

        if trade.stop_distance_pips <= 0:
            raise TradeValidationError("stop_distance_pips must be > 0.")

        if not trade.strategy_name.strip():
            raise TradeValidationError("strategy_name is required.")

        if not trade.timeframe.strip():
            raise TradeValidationError("timeframe is required.")

        if not trade.signal_type.strip():
            raise TradeValidationError("signal_type is required.")

        if not trade.source.strip():
            raise TradeValidationError("source is required.")

        if not trade.created_at.strip():
            raise TradeValidationError("created_at is required.")

        self._validate_directional_price_logic(trade)

    def _validate_directional_price_logic(self, trade: Trade) -> None:
        if trade.direction == "LONG":
            if not (trade.stop_loss < trade.entry < trade.take_profit):
                raise TradeValidationError(
                    "LONG trade must satisfy: stop_loss < entry < take_profit."
                )
            return

        if trade.direction == "SHORT":
            if not (trade.take_profit < trade.entry < trade.stop_loss):
                raise TradeValidationError(
                    "SHORT trade must satisfy: take_profit < entry < stop_loss."
                )
            return

    def _validate_status_specific_fields(self, trade: Trade) -> None:
        if trade.status == TradeStatus.PREPARED:
            if trade.opened_at is not None:
                raise TradeValidationError("PREPARED trade cannot have opened_at.")
            if trade.closed_at is not None:
                raise TradeValidationError("PREPARED trade cannot have closed_at.")
            if trade.exit_price is not None:
                raise TradeValidationError("PREPARED trade cannot have exit_price.")
            if trade.pnl is not None:
                raise TradeValidationError("PREPARED trade cannot have pnl.")
            return

        if trade.status == TradeStatus.SUBMITTED:
            if trade.opened_at is not None:
                raise TradeValidationError("SUBMITTED trade cannot have opened_at.")
            if trade.closed_at is not None:
                raise TradeValidationError("SUBMITTED trade cannot have closed_at.")
            if trade.exit_price is not None:
                raise TradeValidationError("SUBMITTED trade cannot have exit_price.")
            if trade.pnl is not None:
                raise TradeValidationError("SUBMITTED trade cannot have pnl.")
            return

        if trade.status == TradeStatus.OPEN:
            if trade.opened_at is None:
                raise TradeValidationError("OPEN trade must have opened_at.")
            if trade.closed_at is not None:
                raise TradeValidationError("OPEN trade cannot have closed_at.")
            if trade.exit_price is not None:
                raise TradeValidationError("OPEN trade cannot have exit_price.")
            if trade.pnl is not None:
                raise TradeValidationError("OPEN trade cannot have pnl.")
            return

        if trade.status == TradeStatus.CLOSED:
            if trade.opened_at is None:
                raise TradeValidationError("CLOSED trade must have opened_at.")
            if trade.closed_at is None:
                raise TradeValidationError("CLOSED trade must have closed_at.")
            if trade.exit_price is None:
                raise TradeValidationError("CLOSED trade must have exit_price.")
            if trade.pnl is None:
                raise TradeValidationError("CLOSED trade must have pnl.")
            return

        if trade.status == TradeStatus.REJECTED:
            if trade.opened_at is not None:
                raise TradeValidationError("REJECTED trade cannot have opened_at.")
            if trade.closed_at is not None:
                raise TradeValidationError("REJECTED trade cannot have closed_at.")
            if trade.exit_price is not None:
                raise TradeValidationError("REJECTED trade cannot have exit_price.")
            if trade.pnl is not None:
                raise TradeValidationError("REJECTED trade cannot have pnl.")
            return

        if trade.status == TradeStatus.CANCELLED:
            if trade.opened_at is not None:
                raise TradeValidationError("CANCELLED trade cannot have opened_at.")
            if trade.closed_at is not None:
                raise TradeValidationError("CANCELLED trade cannot have closed_at.")
            if trade.exit_price is not None:
                raise TradeValidationError("CANCELLED trade cannot have exit_price.")
            if trade.pnl is not None:
                raise TradeValidationError("CANCELLED trade cannot have pnl.")
            return

        raise TradeValidationError(f"Unsupported trade status: {trade.status.value}")

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()