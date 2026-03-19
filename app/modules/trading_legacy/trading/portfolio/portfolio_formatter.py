from __future__ import annotations

from app.trading.portfolio.portfolio_models import PortfolioDecision


class PortfolioFormatter:
    def format_decision(self, decision: PortfolioDecision) -> str:
        lines: list[str] = []

        lines.append("PORTFOLIO DECISION")
        lines.append("-" * 72)
        lines.append(f"Allowed: {decision.allowed}")
        lines.append(f"Reason: {decision.reason}")
        lines.append("")
        lines.append("Exposure:")
        lines.append(f"  Total active trades: {decision.exposure.total_active_trades}")
        lines.append(f"  Total risk %: {decision.exposure.total_risk_percent:.2f}")

        if decision.exposure.by_currency:
            lines.append("  By currency:")
            for currency, count in sorted(decision.exposure.by_currency.items()):
                lines.append(f"    {currency}: {count}")

        if decision.exposure.by_pair:
            lines.append("  By pair:")
            for pair, count in sorted(decision.exposure.by_pair.items()):
                lines.append(f"    {pair}: {count}")

        if decision.details:
            lines.append("")
            lines.append("Details:")
            for key, value in decision.details.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)
