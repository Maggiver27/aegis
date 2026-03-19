from __future__ import annotations

from app.trading.models.trade import Trade
from app.trading.portfolio.exposure_calculator import ExposureCalculator
from app.trading.portfolio.portfolio_models import (
    PortfolioConfig,
    PortfolioDecision,
)


class PortfolioEngine:
    """
    Decides whether a new trade is allowed into the portfolio.
    """

    def __init__(
        self,
        config: PortfolioConfig | None = None,
    ) -> None:
        self.config = config or PortfolioConfig()
        self.exposure_calculator = ExposureCalculator()

    def evaluate(
        self,
        candidate_trade: Trade,
        existing_trades: list[Trade],
    ) -> PortfolioDecision:
        current_exposure = self.exposure_calculator.calculate(
            existing_trades,
            self.config,
        )

        projected_total_active = current_exposure.total_active_trades + 1
        projected_total_risk = (
            current_exposure.total_risk_percent + candidate_trade.risk_percent
        )

        pair = candidate_trade.pair.strip().upper()
        base, quote = self._split_pair(pair)

        projected_pair_count = current_exposure.by_pair.get(pair, 0) + 1
        projected_base_count = current_exposure.by_currency.get(base, 0) + 1
        projected_quote_count = current_exposure.by_currency.get(quote, 0) + 1

        details = {
            "candidate_pair": pair,
            "candidate_direction": candidate_trade.direction,
            "current_total_active_trades": current_exposure.total_active_trades,
            "projected_total_active_trades": projected_total_active,
            "current_total_risk_percent": current_exposure.total_risk_percent,
            "projected_total_risk_percent": projected_total_risk,
            "projected_pair_count": projected_pair_count,
            "projected_base_currency_count": projected_base_count,
            "projected_quote_currency_count": projected_quote_count,
            "base_currency": base,
            "quote_currency": quote,
        }

        if projected_total_active > self.config.max_active_trades:
            return PortfolioDecision(
                allowed=False,
                reason="max_active_trades_exceeded",
                exposure=current_exposure,
                details=details,
            )

        if projected_total_risk > self.config.max_total_risk_percent:
            return PortfolioDecision(
                allowed=False,
                reason="max_total_risk_percent_exceeded",
                exposure=current_exposure,
                details=details,
            )

        if projected_pair_count > self.config.max_trades_per_pair:
            return PortfolioDecision(
                allowed=False,
                reason="max_trades_per_pair_exceeded",
                exposure=current_exposure,
                details=details,
            )

        if projected_base_count > self.config.max_trades_per_currency:
            return PortfolioDecision(
                allowed=False,
                reason="base_currency_exposure_exceeded",
                exposure=current_exposure,
                details=details,
            )

        if projected_quote_count > self.config.max_trades_per_currency:
            return PortfolioDecision(
                allowed=False,
                reason="quote_currency_exposure_exceeded",
                exposure=current_exposure,
                details=details,
            )

        return PortfolioDecision(
            allowed=True,
            reason="allowed",
            exposure=current_exposure,
            details=details,
        )

    @staticmethod
    def _split_pair(pair: str) -> tuple[str, str]:
        clean = pair.strip().upper()

        if len(clean) == 6:
            return clean[:3], clean[3:]

        return clean[:3], clean[3:] if len(clean) > 3 else "UNK"
