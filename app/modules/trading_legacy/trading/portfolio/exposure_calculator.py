from __future__ import annotations

from app.trading.models.trade import Trade, TradeStatus
from app.trading.portfolio.portfolio_models import PortfolioConfig, PortfolioExposure


class ExposureCalculator:
    """
    Calculates simple portfolio exposure from currently active trades.
    """

    def calculate(
        self,
        trades: list[Trade],
        config: PortfolioConfig,
    ) -> PortfolioExposure:
        active_trades = [trade for trade in trades if self._is_active(trade, config)]

        total_risk_percent = sum(trade.risk_percent for trade in active_trades)

        by_currency: dict[str, int] = {}
        by_pair: dict[str, int] = {}

        for trade in active_trades:
            pair = trade.pair.strip().upper()
            base, quote = self._split_pair(pair)

            by_pair[pair] = by_pair.get(pair, 0) + 1

            for currency in (base, quote):
                by_currency[currency] = by_currency.get(currency, 0) + 1

        return PortfolioExposure(
            total_active_trades=len(active_trades),
            total_risk_percent=total_risk_percent,
            by_currency=by_currency,
            by_pair=by_pair,
        )

    def _is_active(self, trade: Trade, config: PortfolioConfig) -> bool:
        if trade.status == TradeStatus.PREPARED:
            return config.count_prepared_as_active

        if trade.status == TradeStatus.SUBMITTED:
            return config.count_submitted_as_active

        if trade.status == TradeStatus.OPEN:
            return config.count_open_as_active

        return False

    @staticmethod
    def _split_pair(pair: str) -> tuple[str, str]:
        clean = pair.strip().upper()

        if len(clean) == 6:
            return clean[:3], clean[3:]

        return clean[:3], clean[3:] if len(clean) > 3 else "UNK"
