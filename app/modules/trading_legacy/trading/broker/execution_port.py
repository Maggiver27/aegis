from __future__ import annotations

from typing import Protocol

from app.trading.models.trade import Trade


class ExecutionPort(Protocol):
    """
    Abstraction for execution engines.

    Current implementation:
    - PaperExecutionEngine

    Future implementation:
    - MT5ExecutionEngine

    Important:
    This port must not depend on any concrete execution implementation.
    """

    def submit(self, trade: Trade) -> Trade:
        ...

    def open(self, trade: Trade) -> Trade:
        ...

    def reject(self, trade: Trade, *, reason: str) -> Trade:
        ...

    def cancel(self, trade: Trade, *, reason: str) -> Trade:
        ...

    def close(
        self,
        trade: Trade,
        *,
        exit_price: float,
        pnl: float,
    ) -> Trade:
        ...

    def execute_full_cycle(
        self,
        trade: Trade,
        *,
        exit_price: float,
        pnl: float,
    ) -> list[Trade]:
        ...