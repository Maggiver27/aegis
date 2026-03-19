from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PortfolioConfig:
    max_total_risk_percent: float = 3.0
    max_active_trades: int = 6
    max_trades_per_currency: int = 2
    max_trades_per_pair: int = 1
    count_prepared_as_active: bool = True
    count_submitted_as_active: bool = True
    count_open_as_active: bool = True


@dataclass(slots=True)
class PortfolioExposure:
    total_active_trades: int
    total_risk_percent: float
    by_currency: dict[str, int] = field(default_factory=dict)
    by_pair: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class PortfolioDecision:
    allowed: bool
    reason: str
    exposure: PortfolioExposure
    details: dict[str, Any] = field(default_factory=dict)
