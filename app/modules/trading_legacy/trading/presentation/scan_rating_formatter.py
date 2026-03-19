from __future__ import annotations

from app.trading.models.scan_rating import ScanRating


class ScanRatingFormatter:
    """
    Responsible for converting ScanRating objects into readable CLI output.
    """

    def format(self, rating: ScanRating) -> str:
        ratio = rating.score_ratio() * 100

        lines: list[str] = []

        lines.append("===================================")
        lines.append("SCAN RATING")
        lines.append("-----------------------------------")

        lines.append(f"Symbol:        {rating.symbol}")
        lines.append(f"Timeframe:     {rating.timeframe}")
        lines.append(f"Strategy:      {rating.strategy_name}")
        lines.append(f"Direction:     {rating.direction}")

        lines.append("")
        lines.append(
            f"Score:         {rating.score:.2f} / {rating.max_score:.2f}"
        )
        lines.append(f"Score ratio:   {ratio:.2f}%")

        lines.append("")
        lines.append("Factors:")

        for key, value in rating.rating_factors.items():
            lines.append(f"  {key:<20} {value:.2f}")

        lines.append("")
        lines.append("Metadata:")

        for key, value in rating.metadata.items():
            lines.append(f"  {key:<20} {value}")

        lines.append("===================================")

        return "\n".join(lines)

    def format_many(self, ratings: list[ScanRating]) -> str:
        if not ratings:
            return "No scan ratings available."

        blocks = [self.format(r) for r in ratings]
        return "\n\n".join(blocks)