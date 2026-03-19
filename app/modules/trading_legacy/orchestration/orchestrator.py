from __future__ import annotations

from collections import Counter
from typing import Any

from app.trading.data.trade_repository import TradeRepository
from app.trading.execution.paper_execution_engine import PaperExecutionEngine
from app.trading.lifecycle.trade_lifecycle_service import (
    InvalidTradeTransitionError,
    TradeLifecycleService,
    TradeValidationError,
)
from app.trading.market_scanner import MarketScanner
from app.trading.models.trade import TradeStatus
from app.trading.portfolio.portfolio_engine import PortfolioEngine
from app.trading.portfolio.portfolio_formatter import PortfolioFormatter
from app.trading.presentation.scan_rating_formatter import ScanRatingFormatter
from app.trading.presentation.trade_formatter import (
    TradeFormatter,
    TradeFormatterConfig,
)
from app.trading.presentation.trade_statistics_formatter import (
    TradeStatisticsFormatter,
)
from app.trading.presentation.trading_scheduler_formatter import (
    TradingSchedulerFormatter,
)
from app.trading.quality_filter.quality_filter import QualityFilter
from app.trading.query.trade_query_service import TradeQuery, TradeQueryService
from app.trading.risk_management.risk_manager import RiskManager
from app.trading.scheduler.trading_scheduler import TradingScheduler
from app.trading.scoring.scan_rating_service import ScanRatingService
from app.trading.statistics.trade_statistics_service import TradeStatisticsService
from app.trading.strategy_registry import StrategyRegistry


class Orchestrator:
    def __init__(self, event_bus) -> None:
        print("[ORCHESTRATOR] Init start")

        self.event_bus = event_bus
        self.strategy_registry = StrategyRegistry()
        self.market_scanner = MarketScanner(event_bus, self.strategy_registry)
        self.quality_filter = QualityFilter()
        self.scan_rating_service = ScanRatingService()
        self.scan_rating_formatter = ScanRatingFormatter()
        self.risk_manager = RiskManager()
        self.trade_repository = TradeRepository(
            db_path="app/trading/data/trades.db"
        )
        self.trade_lifecycle = TradeLifecycleService()
        self.paper_execution_engine = PaperExecutionEngine(self.trade_lifecycle)
        self.trade_query_service = TradeQueryService()
        self.trade_formatter = TradeFormatter(
            TradeFormatterConfig(show_metadata=True)
        )
        self.trade_statistics_service = TradeStatisticsService()
        self.trade_statistics_formatter = TradeStatisticsFormatter()
        self.trading_scheduler_formatter = TradingSchedulerFormatter()
        self.portfolio_engine = PortfolioEngine()
        self.portfolio_formatter = PortfolioFormatter()

        self.trading_scheduler = TradingScheduler(
            scan_callback=self._scheduler_scan_market,
            paper_execute_callback=self._scheduler_paper_execute_prepared_trades,
        )

        print("[ORCHESTRATOR] Init done")

    def handle_command(self, command: str) -> None:
        print(f"[ORCHESTRATOR] Received command: {command}")

        parts = command.strip().split()
        if not parts:
            print("[ORCHESTRATOR] Empty command")
            return

        action = parts[0]

        try:
            match action:
                case "scan_market":
                    self._handle_scan_market()
                case "scan_rating_test":
                    self._handle_scan_rating_test()
                case "show_trades":
                    self._handle_show_trades(parts)
                case "show_trades_summary":
                    self._handle_show_trades_summary()
                case "show_trade_stats":
                    self._handle_show_trade_stats()
                case "cleanup_prepared_duplicates":
                    self._cleanup_prepared_duplicates()
                case "clear_prepared_trades":
                    self._handle_clear_prepared_trades()
                case "mark_submitted":
                    self._handle_mark_submitted(parts)
                case "mark_open":
                    self._handle_mark_open(parts)
                case "mark_closed":
                    self._handle_mark_closed(parts)
                case "mark_rejected":
                    self._handle_mark_rejected(parts)
                case "mark_cancelled":
                    self._handle_mark_cancelled(parts)
                case "paper_submit":
                    self._handle_paper_submit(parts)
                case "paper_open":
                    self._handle_paper_open(parts)
                case "paper_close":
                    self._handle_paper_close(parts)
                case "paper_reject":
                    self._handle_paper_reject(parts)
                case "paper_cancel":
                    self._handle_paper_cancel(parts)
                case "paper_full_cycle":
                    self._handle_paper_full_cycle(parts)
                case "scheduler_start":
                    self._handle_scheduler_start(parts)
                case "scheduler_stop":
                    self._handle_scheduler_stop()
                case "scheduler_status":
                    self._handle_scheduler_status()
                case "scheduler_run_once":
                    self._handle_scheduler_run_once()
                case "portfolio_check":
                    self._handle_portfolio_check(parts)
                case _:
                    print(f"[ORCHESTRATOR] Unknown command: {action}")

        except (InvalidTradeTransitionError, TradeValidationError) as exc:
            print(f"[ORCHESTRATOR] Lifecycle error: {exc}")
        except ValueError as exc:
            print(f"[ORCHESTRATOR] Validation error: {exc}")
        except Exception as exc:
            print(f"[ORCHESTRATOR] Unexpected error: {exc}")

    def _handle_scan_market(self) -> None:
        self._run_scan_market(verbose=True)

    def _handle_scan_rating_test(self) -> None:
        print("[ORCHESTRATOR] Running scan rating test...")

        scan_results = self.market_scanner.scan()
        scan_count = len(scan_results)

        print(f"[ORCHESTRATOR] Scan results count: {scan_count}")

        if not scan_results:
            print("[ORCHESTRATOR] No scan results to rate")
            return

        ratings = []

        for index, result in enumerate(scan_results, start=1):
            candidate_symbol, candidate_timeframe, candidate_direction = (
                self._extract_candidate_fields(result)
            )

            print(
                f"[ORCHESTRATOR] Rating candidate #{index}: "
                f"symbol={candidate_symbol}, "
                f"timeframe={candidate_timeframe}, "
                f"direction={candidate_direction}"
            )

            rating = self.scan_rating_service.rate(result)
            ratings.append(rating)

        ratings.sort(key=lambda item: item.score, reverse=True)

        print("[ORCHESTRATOR] Scan ratings sorted by score descending")
        print(self.scan_rating_formatter.format_many(ratings))

    def _run_scan_market(self, *, verbose: bool) -> int:
        if verbose:
            print("[ORCHESTRATOR] Running market scan...")

        scan_results = self.market_scanner.scan()
        scan_count = len(scan_results)

        if verbose:
            print(f"[ORCHESTRATOR] Scan results count: {scan_count}")

        if not scan_results:
            if verbose:
                print("[ORCHESTRATOR] No signals")
            return 0

        created = 0
        quality_rejected = 0
        risk_rejected = 0
        portfolio_blocked = 0
        quality_reasons: Counter[str] = Counter()
        risk_reasons: Counter[str] = Counter()
        portfolio_reasons: Counter[str] = Counter()

        ranked_candidates: list[tuple[dict[str, Any], Any]] = []

        for index, result in enumerate(scan_results, start=1):
            candidate_symbol, candidate_timeframe, candidate_direction = (
                self._extract_candidate_fields(result)
            )

            if verbose:
                print(
                    f"[ORCHESTRATOR] Raw candidate #{index}: "
                    f"symbol={candidate_symbol}, "
                    f"timeframe={candidate_timeframe}, "
                    f"direction={candidate_direction}"
                )

            is_valid, quality_reason = self.quality_filter.evaluate(result)

            if not is_valid:
                quality_rejected += 1
                quality_reasons[quality_reason] += 1

                if verbose:
                    print(
                        f"[ORCHESTRATOR] Raw candidate #{index} rejected by QualityFilter: "
                        f"{quality_reason}"
                    )
                continue

            rating = self.scan_rating_service.rate(result)
            enriched_result = self._attach_rating_snapshot_to_result(result, rating)
            ranked_candidates.append((enriched_result, rating))

        ranked_candidates.sort(
            key=lambda item: item[1].score,
            reverse=True,
        )

        if verbose:
            print(
                "[ORCHESTRATOR] Quality-passed candidates sorted by scan rating descending"
            )

        for ranked_index, (result, rating) in enumerate(ranked_candidates, start=1):
            if verbose:
                print(
                    f"[ORCHESTRATOR] Ranked candidate #{ranked_index}: "
                    f"{self._format_scan_rating_line(rating)}"
                )

            trade = self.risk_manager.prepare_trade(result)

            if trade is None:
                risk_rejected += 1
                reason = self.risk_manager.last_rejection_reason or "unknown_reason"
                risk_reasons[reason] += 1

                if verbose:
                    print(
                        f"[ORCHESTRATOR] Ranked candidate #{ranked_index} rejected by RiskManager: "
                        f"{reason}"
                    )
                continue

            if verbose:
                print(
                    f"[ORCHESTRATOR] Ranked candidate #{ranked_index} produced trade: "
                    f"{trade.pair} | {trade.direction} | "
                    f"entry={trade.entry} | "
                    f"sl={trade.stop_loss} | "
                    f"tp={trade.take_profit} | "
                    f"risk={trade.risk_percent:.2f}% | "
                    f"lot={trade.lot_size:.2f} | "
                    f"scan_score={trade.scan_score}"
                )

            existing_trades = self.trade_repository.list_all()
            decision = self.portfolio_engine.evaluate(trade, existing_trades)

            if verbose:
                print(
                    f"[ORCHESTRATOR] Portfolio decision for {trade.pair}: "
                    f"{self._format_portfolio_decision_line(decision)}"
                )

            if not decision.allowed:
                portfolio_blocked += 1
                portfolio_reasons[decision.reason] += 1

                if verbose:
                    print(
                        f"[ORCHESTRATOR] Trade blocked by portfolio gate: "
                        f"{trade.pair} ({decision.reason})"
                    )
                continue

            self.trade_repository.save(trade)
            created += 1

            if verbose:
                print(
                    f"[ORCHESTRATOR] Trade saved: {trade.trade_id} | "
                    f"{trade.pair} | {trade.direction} | "
                    f"scan_score={trade.scan_score}"
                )

        if verbose:
            self._print_scan_summary(
                scan_count=scan_count,
                created=created,
                quality_rejected=quality_rejected,
                risk_rejected=risk_rejected,
                portfolio_blocked=portfolio_blocked,
                quality_reasons=quality_reasons,
                risk_reasons=risk_reasons,
                portfolio_reasons=portfolio_reasons,
            )

        return created

    def _handle_show_trades(self, parts: list[str]) -> None:
        print("[ORCHESTRATOR] Loading trades from repository...")

        trades = self.trade_repository.list_all()
        query = self._parse_trade_query(parts[1:])
        filtered = self.trade_query_service.filter_trades(trades, query)

        print(f"[ORCHESTRATOR] Trades matched: {len(filtered)}")

        formatted = self.trade_formatter.format_many(filtered)
        print(formatted)

    def _handle_show_trades_summary(self) -> None:
        print("[ORCHESTRATOR] Loading trade summary...")

        trades = self.trade_repository.list_all()
        summary = self.trade_query_service.summarize(trades)

        total = sum(summary.values())
        print(f"[ORCHESTRATOR] Total trades: {total}")

        if not summary:
            print("[ORCHESTRATOR] No trades found")
            return

        for status, count in summary.items():
            print(f"{status}: {count}")

    def _handle_show_trade_stats(self) -> None:
        print("[ORCHESTRATOR] Loading trade statistics...")

        trades = self.trade_repository.list_all()
        stats = self.trade_statistics_service.calculate(trades)
        formatted = self.trade_statistics_formatter.format(stats)

        print(formatted)

    def _cleanup_prepared_duplicates(self) -> None:
        print("[ORCHESTRATOR] Cleaning PREPARED duplicates...")

        removed = self.trade_repository.cleanup_prepared_duplicates()

        print(f"[ORCHESTRATOR] PREPARED duplicates removed: {removed}")

    def _handle_clear_prepared_trades(self) -> None:
        print("[ORCHESTRATOR] Clearing PREPARED trades...")

        trades = self.trade_repository.list_all()
        prepared_trades = self.trade_query_service.filter_trades(
            trades,
            TradeQuery(status=TradeStatus.PREPARED),
        )

        if not prepared_trades:
            print("[ORCHESTRATOR] No PREPARED trades found")
            return

        removed = 0

        for trade in prepared_trades:
            deleted = self.trade_repository.delete(trade.trade_id)
            if deleted:
                removed += 1
                print(
                    f"[ORCHESTRATOR] Removed PREPARED trade: "
                    f"{trade.trade_id} | {trade.pair} | {trade.direction}"
                )

        print(f"[ORCHESTRATOR] PREPARED trades removed: {removed}")

    def _handle_mark_submitted(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: mark_submitted <trade_id>")
            return

        trade_id = parts[1]
        trade = self.trade_repository.get(trade_id)

        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.trade_lifecycle.mark_submitted(trade)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} -> SUBMITTED")

    def _handle_mark_open(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: mark_open <trade_id>")
            return

        trade_id = parts[1]
        trade = self.trade_repository.get(trade_id)

        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.trade_lifecycle.mark_open(trade)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} -> OPEN")

    def _handle_mark_closed(self, parts: list[str]) -> None:
        if len(parts) < 4:
            print("[ORCHESTRATOR] Usage: mark_closed <trade_id> <exit_price> <pnl>")
            return

        trade_id = parts[1]

        try:
            exit_price = float(parts[2])
            pnl = float(parts[3])
        except ValueError:
            print("[ORCHESTRATOR] exit_price and pnl must be numbers")
            return

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.trade_lifecycle.mark_closed(
            trade,
            exit_price=exit_price,
            pnl=pnl,
        )
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} -> CLOSED")

    def _handle_mark_rejected(self, parts: list[str]) -> None:
        if len(parts) < 3:
            print("[ORCHESTRATOR] Usage: mark_rejected <trade_id> <reason>")
            return

        trade_id = parts[1]
        reason = " ".join(parts[2:])

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.trade_lifecycle.mark_rejected(
            trade,
            reason=reason,
        )
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} -> REJECTED")

    def _handle_mark_cancelled(self, parts: list[str]) -> None:
        if len(parts) < 3:
            print("[ORCHESTRATOR] Usage: mark_cancelled <trade_id> <reason>")
            return

        trade_id = parts[1]
        reason = " ".join(parts[2:])

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.trade_lifecycle.mark_cancelled(
            trade,
            reason=reason,
        )
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} -> CANCELLED")

    def _handle_paper_submit(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: paper_submit <trade_id>")
            return

        trade_id = parts[1]
        trade = self.trade_repository.get(trade_id)

        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.paper_execution_engine.submit(trade)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} submitted in paper mode.")

    def _handle_paper_open(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: paper_open <trade_id>")
            return

        trade_id = parts[1]
        trade = self.trade_repository.get(trade_id)

        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.paper_execution_engine.open(trade)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} opened in paper mode.")

    def _handle_paper_close(self, parts: list[str]) -> None:
        if len(parts) < 4:
            print("[ORCHESTRATOR] Usage: paper_close <trade_id> <exit_price> <pnl>")
            return

        trade_id = parts[1]

        try:
            exit_price = float(parts[2])
            pnl = float(parts[3])
        except ValueError:
            print("[ORCHESTRATOR] exit_price and pnl must be numbers")
            return

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.paper_execution_engine.close(
            trade,
            exit_price=exit_price,
            pnl=pnl,
        )
        self.trade_repository.save(updated)

        print(
            f"[ORCHESTRATOR] Trade {trade_id} closed in paper mode "
            f"at {exit_price} with pnl {pnl}."
        )

    def _handle_paper_reject(self, parts: list[str]) -> None:
        if len(parts) < 3:
            print("[ORCHESTRATOR] Usage: paper_reject <trade_id> <reason>")
            return

        trade_id = parts[1]
        reason = " ".join(parts[2:])

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.paper_execution_engine.reject(trade, reason=reason)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} rejected in paper mode: {reason}")

    def _handle_paper_cancel(self, parts: list[str]) -> None:
        if len(parts) < 3:
            print("[ORCHESTRATOR] Usage: paper_cancel <trade_id> <reason>")
            return

        trade_id = parts[1]
        reason = " ".join(parts[2:])

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        updated = self.paper_execution_engine.cancel(trade, reason=reason)
        self.trade_repository.save(updated)

        print(f"[ORCHESTRATOR] Trade {trade_id} cancelled in paper mode: {reason}")

    def _handle_paper_full_cycle(self, parts: list[str]) -> None:
        if len(parts) < 4:
            print("[ORCHESTRATOR] Usage: paper_full_cycle <trade_id> <exit_price> <pnl>")
            return

        trade_id = parts[1]

        try:
            exit_price = float(parts[2])
            pnl = float(parts[3])
        except ValueError:
            print("[ORCHESTRATOR] exit_price and pnl must be numbers")
            return

        trade = self.trade_repository.get(trade_id)
        if trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        results = self.paper_execution_engine.execute_full_cycle(
            trade,
            exit_price=exit_price,
            pnl=pnl,
        )

        final_trade = results[-1]
        self.trade_repository.save(final_trade)

        print(f"[ORCHESTRATOR] Trade {trade_id} submitted in paper mode.")
        print(f"[ORCHESTRATOR] Trade {trade_id} opened in paper mode.")
        print(
            f"[ORCHESTRATOR] Trade {trade_id} closed in paper mode "
            f"at {exit_price} with pnl {pnl}."
        )

    def _handle_scheduler_start(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: scheduler_start <interval_seconds> [paper]")
            return

        try:
            interval_seconds = int(parts[1])
        except ValueError:
            print("[ORCHESTRATOR] interval_seconds must be integer")
            return

        auto_execute_paper = len(parts) >= 3 and parts[2].lower() == "paper"

        self.trading_scheduler.start(
            interval_seconds=interval_seconds,
            auto_execute_paper=auto_execute_paper,
        )

        print(
            "[ORCHESTRATOR] Scheduler started "
            f"(interval={interval_seconds}s, auto_execute_paper={auto_execute_paper})"
        )

    def _handle_scheduler_stop(self) -> None:
        self.trading_scheduler.stop()
        print("[ORCHESTRATOR] Scheduler stopped")

    def _handle_scheduler_status(self) -> None:
        status = self.trading_scheduler.get_status()
        formatted = self.trading_scheduler_formatter.format(status)
        print(formatted)

    def _handle_scheduler_run_once(self) -> None:
        print("[ORCHESTRATOR] Scheduler manual run start")
        self.trading_scheduler.run_once()
        print("[ORCHESTRATOR] Scheduler manual run finished")

    def _handle_portfolio_check(self, parts: list[str]) -> None:
        if len(parts) < 2:
            print("[ORCHESTRATOR] Usage: portfolio_check <trade_id>")
            return

        trade_id = parts[1]
        candidate_trade = self.trade_repository.get(trade_id)

        if candidate_trade is None:
            print("[ORCHESTRATOR] Trade not found")
            return

        existing_trades = [
            trade
            for trade in self.trade_repository.list_all()
            if trade.trade_id != trade_id
        ]

        decision = self.portfolio_engine.evaluate(candidate_trade, existing_trades)
        formatted = self.portfolio_formatter.format_decision(decision)
        print(formatted)

    def _scheduler_scan_market(self) -> None:
        created = self._run_scan_market(verbose=False)
        print(f"[SCHEDULER] Scan finished. Trades created: {created}")

    def _scheduler_paper_execute_prepared_trades(self) -> None:
        trades = self.trade_repository.list_all()
        prepared = self.trade_query_service.filter_trades(
            trades,
            TradeQuery(status=TradeStatus.PREPARED),
        )

        if not prepared:
            print("[SCHEDULER] No PREPARED trades for paper execution")
            return

        executed = 0

        for trade in prepared:
            exit_price = trade.take_profit
            pnl = 10.0

            results = self.paper_execution_engine.execute_full_cycle(
                trade,
                exit_price=exit_price,
                pnl=pnl,
            )

            final_trade = results[-1]
            self.trade_repository.save(final_trade)
            executed += 1

        print(f"[SCHEDULER] Paper execution finished. Trades closed: {executed}")

    def _parse_trade_query(self, parts: list[str]) -> TradeQuery:
        query = TradeQuery()

        i = 0
        while i < len(parts):
            token = parts[i].lower()

            if token == "status":
                if i + 1 >= len(parts):
                    raise ValueError("show_trades status <value>")
                query.status = self.trade_query_service.parse_status(parts[i + 1])
                i += 2
                continue

            if token == "pair":
                if i + 1 >= len(parts):
                    raise ValueError("show_trades pair <value>")
                query.pair = parts[i + 1]
                i += 2
                continue

            if token == "strategy":
                if i + 1 >= len(parts):
                    raise ValueError("show_trades strategy <value>")
                query.strategy_name = parts[i + 1]
                i += 2
                continue

            if token == "timeframe":
                if i + 1 >= len(parts):
                    raise ValueError("show_trades timeframe <value>")
                query.timeframe = parts[i + 1]
                i += 2
                continue

            if token == "limit":
                if i + 1 >= len(parts):
                    raise ValueError("show_trades limit <number>")
                try:
                    query.limit = int(parts[i + 1])
                except ValueError as exc:
                    raise ValueError("limit must be integer") from exc
                i += 2
                continue

            raise ValueError(f"Unsupported show_trades filter: {parts[i]}")

        return query

    @staticmethod
    def _attach_rating_snapshot_to_result(
        result: Any,
        rating: Any,
    ) -> dict[str, Any]:
        if isinstance(result, dict):
            enriched = dict(result)
        else:
            enriched = {}

        enriched["scan_score"] = float(rating.score)
        enriched["scan_score_ratio"] = float(rating.score_ratio())
        enriched["scan_rating_factors"] = dict(rating.rating_factors)

        return enriched

    @staticmethod
    def _extract_candidate_fields(result) -> tuple[str | None, str | None, str | None]:
        symbol = getattr(result, "symbol", None)
        timeframe = getattr(result, "timeframe", None)
        direction = getattr(result, "direction", None)

        if isinstance(result, dict):
            symbol = result.get("symbol", symbol)
            timeframe = result.get("timeframe", timeframe)
            direction = result.get("direction", direction)

        return symbol, timeframe, direction

    @staticmethod
    def _format_scan_rating_line(rating) -> str:
        return (
            f"score={rating.score:.2f}/{rating.max_score:.2f}, "
            f"ratio={rating.score_ratio() * 100:.2f}%, "
            f"direction={rating.direction}, "
            f"symbol={rating.symbol}, "
            f"timeframe={rating.timeframe}, "
            f"strategy={rating.strategy_name}"
        )

    @staticmethod
    def _format_portfolio_decision_line(decision) -> str:
        details = decision.details or {}

        current_total_risk = details.get("current_total_risk_percent")
        projected_total_risk = details.get("projected_total_risk_percent")
        current_total_active = details.get("current_total_active_trades")
        projected_total_active = details.get("projected_total_active_trades")
        projected_pair_count = details.get("projected_pair_count")
        projected_base_count = details.get("projected_base_currency_count")
        projected_quote_count = details.get("projected_quote_currency_count")
        base_currency = details.get("base_currency")
        quote_currency = details.get("quote_currency")

        return (
            f"allowed={decision.allowed}, "
            f"reason={decision.reason}, "
            f"risk={current_total_risk}->{projected_total_risk}, "
            f"active={current_total_active}->{projected_total_active}, "
            f"pair_count={projected_pair_count}, "
            f"{base_currency}_count={projected_base_count}, "
            f"{quote_currency}_count={projected_quote_count}"
        )

    @staticmethod
    def _print_counter_block(title: str, counter: Counter[str]) -> None:
        print(title)

        if not counter:
            print("[ORCHESTRATOR]   none")
            return

        for reason, count in counter.most_common():
            print(f"[ORCHESTRATOR]   {reason}: {count}")

    def _print_scan_summary(
        self,
        *,
        scan_count: int,
        created: int,
        quality_rejected: int,
        risk_rejected: int,
        portfolio_blocked: int,
        quality_reasons: Counter[str],
        risk_reasons: Counter[str],
        portfolio_reasons: Counter[str],
    ) -> None:
        print("[ORCHESTRATOR] Scan summary:")
        print(f"[ORCHESTRATOR]   Scan results total: {scan_count}")
        print(f"[ORCHESTRATOR]   Rejected by QualityFilter: {quality_rejected}")
        print(f"[ORCHESTRATOR]   Rejected by RiskManager: {risk_rejected}")
        print(f"[ORCHESTRATOR]   Blocked by PortfolioEngine: {portfolio_blocked}")
        print(f"[ORCHESTRATOR]   Trades created: {created}")

        self._print_counter_block(
            "[ORCHESTRATOR] Quality rejection reasons:",
            quality_reasons,
        )
        self._print_counter_block(
            "[ORCHESTRATOR] Risk rejection reasons:",
            risk_reasons,
        )
        self._print_counter_block(
            "[ORCHESTRATOR] Portfolio block reasons:",
            portfolio_reasons,
        )