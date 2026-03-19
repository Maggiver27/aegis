from __future__ import annotations

from app.trading.broker.execution_port import ExecutionPort
from app.trading.lifecycle.trade_lifecycle_service import TradeLifecycleService
from app.trading.models.trade import Trade


class PaperExecutionEngine(ExecutionPort):
    """
    Simulated execution engine for local/paper trading flow.

    Purpose:
    - provide an execution layer before MT5 integration
    - let the system exercise realistic trade lifecycle transitions
    - keep execution rules out of orchestrator

    Architectural role:
    - this class implements ExecutionPort
    - orchestrator can use this engine now
    - future MT5ExecutionEngine should implement the same port
    """

    def __init__(self, lifecycle_service: TradeLifecycleService) -> None:
        self.lifecycle_service = lifecycle_service

    def submit(self, trade: Trade) -> Trade:
        return self.lifecycle_service.mark_submitted(trade)

    def open(self, trade: Trade) -> Trade:
        return self.lifecycle_service.mark_open(trade)

    def reject(self, trade: Trade, *, reason: str) -> Trade:
        return self.lifecycle_service.mark_rejected(trade, reason=reason)

    def cancel(self, trade: Trade, *, reason: str) -> Trade:
        return self.lifecycle_service.mark_cancelled(trade, reason=reason)

    def close(
        self,
        trade: Trade,
        *,
        exit_price: float,
        pnl: float,
    ) -> Trade:
        return self.lifecycle_service.mark_closed(
            trade,
            exit_price=exit_price,
            pnl=pnl,
        )

    def execute_full_cycle(
        self,
        trade: Trade,
        *,
        exit_price: float,
        pnl: float,
    ) -> list[Trade]:
        """
        Convenience method for quick paper simulation:
        PREPARED -> SUBMITTED -> OPEN -> CLOSED
        """
        submitted = self.submit(trade)
        opened = self.open(submitted)
        closed = self.close(
            opened,
            exit_price=exit_price,
            pnl=pnl,
        )
        return [submitted, opened, closed]