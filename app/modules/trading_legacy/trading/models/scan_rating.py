from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ScanRating:
    """
    Domain model representing a scored trading signal candidate.

    Architectural role:
    - produced by ScanRatingService
    - consumed by later pipeline stages (RiskManager / PortfolioEngine)
    - contains score and explanation factors

    This model does NOT perform any calculations.
    It is purely a structured data container.
    """

    symbol: str
    timeframe: str
    strategy_name: str
    direction: str | None

    score: float
    max_score: float

    rating_factors: dict[str, float] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def score_ratio(self) -> float:
        """
        Return normalized score ratio (0.0 - 1.0).
        """
        if self.max_score == 0:
            return 0.0
        return self.score / self.max_score

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize rating for logging / storage / debugging.
        """
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy_name": self.strategy_name,
            "direction": self.direction,
            "score": self.score,
            "max_score": self.max_score,
            "score_ratio": self.score_ratio(),
            "rating_factors": self.rating_factors,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }