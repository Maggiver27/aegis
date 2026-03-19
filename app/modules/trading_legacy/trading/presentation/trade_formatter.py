from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.trading.models.trade import Trade


@dataclass(slots=True)
class TradeFormatterConfig:
    separator: str = "-" * 72
    show_metadata: bool = False


class TradeFormatter:
    """
    Formats Trade objects into readable terminal output.

    Purpose:
    - keep presentation logic out of orchestrator
    - avoid raw dataclass dumps in CLI
    - make future API/UI/reporting formatting easier
    """

    def __init__(self, config: TradeFormatterConfig | None = None) -> None:
        self.config = config or TradeFormatterConfig()

    def format_trade(self, trade: Trade) -> str:
        lines: list[str] = []

        lines.append(
            f"{trade.pair} | {trade.direction} | {trade.status.value.upper()} | "
            f"{trade.strategy_name} | {trade.timeframe}"
        )

        lines.append(
            f"ID: {trade.trade_id or '-'}"
        )

        lines.append(
            f"Entry: {trade.entry:.5f} | SL: {trade.stop_loss:.5f} | "
            f"TP: {trade.take_profit:.5f}"
        )

        lines.append(
            f"Lot: {trade.lot_size:.2f} | Risk%: {trade.risk_percent:.2f} | "
            f"Risk amount: {trade.risk_amount:.2f}"
        )

        lines.append(
            f"Stop distance: {trade.stop_distance_price:.5f} price | "
            f"{trade.stop_distance_pips:.2f} pips"
        )

        lines.append(
            f"Sizing: {trade.sizing_mode} | Pip size: {trade.pip_size:.5f} | "
            f"Pip value/std lot: {self._fmt_optional_float(trade.pip_value_per_standard_lot)}"
        )

        lines.append(
            f"Signal: {trade.signal_type} | Source: {trade.source}"
        )

        lines.append(
            f"Created: {trade.created_at}"
        )

        if trade.scan_score is not None or trade.scan_score_ratio is not None:
            lines.append(
                "Scan rating: "
                f"score={self._fmt_optional_float(trade.scan_score)} | "
                f"ratio={self._fmt_ratio(trade.scan_score_ratio)}"
            )

        if trade.scan_rating_factors:
            lines.append("Scan rating factors:")
            for key, value in sorted(trade.scan_rating_factors.items()):
                lines.append(f"  - {key}: {value:.2f}")

        if trade.opened_at is not None:
            lines.append(f"Opened: {trade.opened_at}")

        if trade.closed_at is not None:
            lines.append(f"Closed: {trade.closed_at}")

        if trade.exit_price is not None:
            lines.append(f"Exit price: {trade.exit_price:.5f}")

        if trade.pnl is not None:
            lines.append(f"PnL: {trade.pnl:.2f}")

        if self.config.show_metadata and trade.metadata:
            lines.append("Metadata:")
            for key, value in sorted(trade.metadata.items()):
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines)

    def format_many(self, trades: Iterable[Trade]) -> str:
        trade_list = list(trades)
        if not trade_list:
            return "[TRADES] No trades found"

        blocks = [self.format_trade(trade) for trade in trade_list]
        return f"\n{self.config.separator}\n".join(blocks)

    @staticmethod
    def _fmt_optional_float(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}"

    @staticmethod
    def _fmt_ratio(value: float | None) -> str:
        if value is None:
            return "-"
        return f"{value * 100:.2f}%"