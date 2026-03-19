from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


class MarketScannerProtocol(Protocol):
    def scan(self) -> list[Any]:
        """
        Return a list of market scan results.
        """
        ...


class RuleEngineProtocol(Protocol):
    def evaluate_many(self, market_scan_results: list[Any]) -> list[Any]:
        """
        Return normalized rule evaluations / trade decisions.
        """
        ...


class RiskManagerProtocol(Protocol):
    def prepare_trade(self, decision: Any) -> Any:
        """
        Build a trade object from a trading decision.
        Return None if trade cannot be prepared.
        """
        ...


class TradeRepositoryProtocol(Protocol):
    def save(self, trade: Any) -> Any:
        """
        Persist trade/setup and optionally return stored object or id.
        """
        ...


@dataclass(slots=True)
class TradingCycleResult:
    scanned_count: int = 0
    evaluated_count: int = 0
    trade_candidates_count: int = 0
    prepared_count: int = 0
    saved_count: int = 0
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)
    saved_trades: list[Any] = field(default_factory=list)
    finished_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TradingService:
    """
    TradingService glues together the trading pipeline:

        MarketScanner
            -> RuleEngine
            -> RiskManager
            -> TradeRepository

    Architecture rules:
    - scanner finds opportunities
    - rule engine evaluates according to ACTIVE strategy
    - risk manager converts decision into trade with risk rules
    - repository persists the final trade/setup
    - TradingService orchestrates only; it does not own strategy logic
    """

    def __init__(
        self,
        market_scanner: MarketScannerProtocol,
        rule_engine: RuleEngineProtocol,
        risk_manager: RiskManagerProtocol,
        trade_repository: TradeRepositoryProtocol,
    ) -> None:
        self._market_scanner = market_scanner
        self._rule_engine = rule_engine
        self._risk_manager = risk_manager
        self._trade_repository = trade_repository

    def run_market_cycle(self) -> TradingCycleResult:
        result = TradingCycleResult()

        try:
            scan_results = self._market_scanner.scan()
        except Exception as exc:
            result.errors.append(f"Market scan failed: {exc}")
            result.finished_at = datetime.now(timezone.utc)
            return result

        result.scanned_count = len(scan_results)

        try:
            decisions = self._rule_engine.evaluate_many(scan_results)
        except Exception as exc:
            result.errors.append(f"Rule engine evaluation failed: {exc}")
            result.finished_at = datetime.now(timezone.utc)
            return result

        result.evaluated_count = len(decisions)

        for decision in decisions:
            try:
                if not self._should_trade(decision):
                    result.skipped_count += 1
                    continue

                result.trade_candidates_count += 1

                trade = self._risk_manager.prepare_trade(decision)
                if trade is None:
                    result.skipped_count += 1
                    continue

                result.prepared_count += 1

                saved_trade = self._trade_repository.save(trade)
                result.saved_count += 1
                result.saved_trades.append(saved_trade if saved_trade is not None else trade)

            except Exception as exc:
                symbol = self._safe_read(decision, "symbol", "UNKNOWN")
                timeframe = self._safe_read(decision, "timeframe", "UNKNOWN")
                result.errors.append(
                    f"Trade pipeline failed for {symbol} {timeframe}: {exc}"
                )

        result.finished_at = datetime.now(timezone.utc)
        return result

    def run_for_scan_results(self, scan_results: list[Any]) -> TradingCycleResult:
        """
        Optional helper for testing or external orchestration when scan results
        are already available and should not be fetched again.
        """
        result = TradingCycleResult(scanned_count=len(scan_results))

        try:
            decisions = self._rule_engine.evaluate_many(scan_results)
        except Exception as exc:
            result.errors.append(f"Rule engine evaluation failed: {exc}")
            result.finished_at = datetime.now(timezone.utc)
            return result

        result.evaluated_count = len(decisions)

        for decision in decisions:
            try:
                if not self._should_trade(decision):
                    result.skipped_count += 1
                    continue

                result.trade_candidates_count += 1

                trade = self._risk_manager.prepare_trade(decision)
                if trade is None:
                    result.skipped_count += 1
                    continue

                result.prepared_count += 1

                saved_trade = self._trade_repository.save(trade)
                result.saved_count += 1
                result.saved_trades.append(saved_trade if saved_trade is not None else trade)

            except Exception as exc:
                symbol = self._safe_read(decision, "symbol", "UNKNOWN")
                timeframe = self._safe_read(decision, "timeframe", "UNKNOWN")
                result.errors.append(
                    f"Trade pipeline failed for {symbol} {timeframe}: {exc}"
                )

        result.finished_at = datetime.now(timezone.utc)
        return result

    @staticmethod
    def _should_trade(decision: Any) -> bool:
        if isinstance(decision, dict):
            value = decision.get("should_trade", False)
        else:
            value = getattr(decision, "should_trade", False)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}

        return False

    @staticmethod
    def _safe_read(obj: Any, field_name: str, default: str) -> str:
        if isinstance(obj, dict):
            value = obj.get(field_name, default)
            return str(value) if value is not None else default

        value = getattr(obj, field_name, default)
        return str(value) if value is not None else default