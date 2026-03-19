from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


class StrategyProtocol(Protocol):
    name: str

    def evaluate(self, market_scan_result: Any) -> Any:
        """
        Strategy returns raw signal/decision.
        Supported practical outputs:
        - dict
        - object with attributes
        - None
        """
        ...


class StrategyRegistryProtocol(Protocol):
    def get_active_strategy(self) -> StrategyProtocol:
        """
        Return currently active strategy instance selected from config.
        """
        ...


@dataclass(slots=True)
class RuleEvaluation:
    symbol: str
    timeframe: str
    strategy_name: str
    action: str
    confidence: float
    should_trade: bool
    reason: str
    direction: str | None = None
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RuleEngine:
    """
    RuleEngine:
    - gets ACTIVE strategy only from StrategyRegistry
    - normalizes raw strategy output
    - applies minimal quality gate before trade reaches RiskManager

    Important:
    - strategy selection does NOT come from request
    - RuleEngine does NOT decide which strategy is active
    """

    def __init__(
        self,
        strategy_registry: StrategyRegistryProtocol,
        *,
        min_confidence: float = 0.60,
        min_risk_reward: float = 1.50,
        logger: logging.Logger | None = None,
    ) -> None:
        self._strategy_registry = strategy_registry
        self._min_confidence = max(0.0, float(min_confidence))
        self._min_risk_reward = max(0.0, float(min_risk_reward))
        self._logger = logger or logging.getLogger(__name__)

    def evaluate(self, market_scan_result: Any) -> RuleEvaluation:
        strategy = self._strategy_registry.get_active_strategy()
        raw_signal = strategy.evaluate(market_scan_result)

        symbol = self._read_symbol(market_scan_result)
        timeframe = self._read_timeframe(market_scan_result)
        strategy_name = getattr(strategy, "name", strategy.__class__.__name__)

        self._logger.debug(
            "Evaluating strategy '%s' for %s/%s",
            strategy_name,
            symbol,
            timeframe,
        )

        normalized = self._normalize_signal(
            raw_signal=raw_signal,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
        )

        return self._apply_quality_gate(normalized)

    def evaluate_many(self, market_scan_results: list[Any]) -> list[RuleEvaluation]:
        return [self.evaluate(item) for item in market_scan_results]

    def _normalize_signal(
        self,
        raw_signal: Any,
        symbol: str,
        timeframe: str,
        strategy_name: str,
    ) -> RuleEvaluation:
        if raw_signal is None:
            return RuleEvaluation(
                symbol=symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                action="HOLD",
                confidence=0.0,
                should_trade=False,
                reason="Strategy returned no signal.",
                direction=None,
                metadata={},
            )

        data = self._to_dict(raw_signal)

        action_raw = data.get("action") or data.get("signal") or data.get("decision")
        action = self._normalize_action(action_raw)

        confidence_raw = data.get("confidence", 0.0)
        confidence = self._to_confidence(confidence_raw)

        reason_raw = data.get("reason")
        reason = self._to_reason(reason_raw)

        direction_raw = data.get("direction") or data.get("bias") or data.get("side") or action
        direction = self._normalize_direction(direction_raw)

        entry = self._to_float_or_none(data.get("entry"))
        stop_loss = self._to_float_or_none(data.get("stop_loss") or data.get("sl"))
        take_profit = self._to_float_or_none(data.get("take_profit") or data.get("tp"))

        should_trade = self._resolve_should_trade(
            explicit_value=data.get("should_trade"),
            action=action,
            direction=direction,
        )

        metadata = {
            k: v
            for k, v in data.items()
            if k
            not in {
                "action",
                "signal",
                "decision",
                "confidence",
                "reason",
                "direction",
                "bias",
                "side",
                "entry",
                "stop_loss",
                "sl",
                "take_profit",
                "tp",
                "should_trade",
            }
        }

        return RuleEvaluation(
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            action=action,
            confidence=confidence,
            should_trade=should_trade,
            reason=reason,
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata,
        )

    def _apply_quality_gate(self, evaluation: RuleEvaluation) -> RuleEvaluation:
        """
        Minimal quality gate for MVP:
        1. HOLD never trades
        2. should_trade must be True
        3. confidence must be >= threshold
        4. direction must match action
        5. entry/SL/TP must exist for trade candidates
        6. SL and TP must be logically placed
        7. RR must be >= threshold
        """

        if evaluation.action == "HOLD":
            self._logger.debug("Quality gate: rejecting HOLD action")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: HOLD action.",
            )

        if not evaluation.should_trade:
            self._logger.debug("Quality gate: rejecting should_trade=False")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: should_trade is False.",
            )

        if evaluation.confidence < self._min_confidence:
            self._logger.debug(
                "Quality gate: rejecting confidence %.2f < %.2f",
                evaluation.confidence,
                self._min_confidence,
            )
            return self._reject(
                evaluation,
                reason=(
                    f"Rejected by RuleEngine: confidence {evaluation.confidence:.2f} "
                    f"is below threshold {self._min_confidence:.2f}."
                ),
            )

        if not self._is_action_direction_consistent(evaluation.action, evaluation.direction):
            self._logger.debug("Quality gate: rejecting action/direction mismatch")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: action/direction mismatch.",
            )

        if (
            evaluation.entry is None
            or evaluation.stop_loss is None
            or evaluation.take_profit is None
        ):
            self._logger.debug("Quality gate: rejecting missing price levels")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: missing entry/SL/TP.",
            )

        if (
            evaluation.entry <= 0
            or evaluation.stop_loss <= 0
            or evaluation.take_profit <= 0
        ):
            self._logger.debug("Quality gate: rejecting non-positive entry/SL/TP")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: non-positive entry/SL/TP.",
            )

        if not self._is_trade_geometry_valid(evaluation):
            self._logger.debug("Quality gate: rejecting invalid price geometry")
            return self._reject(
                evaluation,
                reason="Rejected by RuleEngine: invalid price geometry for direction.",
            )

        rr = self._calculate_risk_reward(
            entry=evaluation.entry,
            stop_loss=evaluation.stop_loss,
            take_profit=evaluation.take_profit,
        )

        if rr < self._min_risk_reward:
            self._logger.debug(
                "Quality gate: rejecting RR %.2f < %.2f",
                rr,
                self._min_risk_reward,
            )
            return self._reject(
                evaluation,
                reason=(
                    f"Rejected by RuleEngine: risk/reward {rr:.2f} "
                    f"is below threshold {self._min_risk_reward:.2f}."
                ),
            )

        updated_metadata = dict(evaluation.metadata)
        updated_metadata.update(
            {
                "quality_gate_passed": True,
                "risk_reward": rr,
                "min_confidence_threshold": self._min_confidence,
                "min_risk_reward_threshold": self._min_risk_reward,
            }
        )

        self._logger.debug(
            "Quality gate: accepted evaluation for %s/%s",
            evaluation.symbol,
            evaluation.timeframe,
        )

        return RuleEvaluation(
            symbol=evaluation.symbol,
            timeframe=evaluation.timeframe,
            strategy_name=evaluation.strategy_name,
            action=evaluation.action,
            confidence=evaluation.confidence,
            should_trade=True,
            reason=evaluation.reason,
            direction=evaluation.direction,
            entry=evaluation.entry,
            stop_loss=evaluation.stop_loss,
            take_profit=evaluation.take_profit,
            metadata=updated_metadata,
            evaluated_at=evaluation.evaluated_at,
        )

    def _reject(self, evaluation: RuleEvaluation, reason: str) -> RuleEvaluation:
        updated_metadata = dict(evaluation.metadata)
        updated_metadata["quality_gate_passed"] = False

        self._logger.debug("Quality gate: final reject reason: %s", reason)

        return RuleEvaluation(
            symbol=evaluation.symbol,
            timeframe=evaluation.timeframe,
            strategy_name=evaluation.strategy_name,
            action="HOLD",
            confidence=evaluation.confidence,
            should_trade=False,
            reason=reason,
            direction=evaluation.direction,
            entry=evaluation.entry,
            stop_loss=evaluation.stop_loss,
            take_profit=evaluation.take_profit,
            metadata=updated_metadata,
            evaluated_at=evaluation.evaluated_at,
        )

    @staticmethod
    def _read_symbol(market_scan_result: Any) -> str:
        if isinstance(market_scan_result, dict):
            value = market_scan_result.get("symbol")
            return str(value) if value is not None else "UNKNOWN"

        value = getattr(market_scan_result, "symbol", None)
        return str(value) if value is not None else "UNKNOWN"

    @staticmethod
    def _read_timeframe(market_scan_result: Any) -> str:
        if isinstance(market_scan_result, dict):
            value = market_scan_result.get("timeframe")
            return str(value) if value is not None else "UNKNOWN"

        value = getattr(market_scan_result, "timeframe", None)
        return str(value) if value is not None else "UNKNOWN"

    def _to_dict(self, raw_signal: Any) -> dict[str, Any]:
        if isinstance(raw_signal, dict):
            return raw_signal

        if hasattr(raw_signal, "model_dump"):
            dumped = raw_signal.model_dump()
            if isinstance(dumped, dict):
                return dumped

        if hasattr(raw_signal, "__dict__"):
            return {
                key: value
                for key, value in vars(raw_signal).items()
                if not key.startswith("_")
            }

        self._logger.warning(
            "Unsupported raw signal type: %s",
            type(raw_signal).__name__,
        )
        return {"value": raw_signal}

    @staticmethod
    def _normalize_action(value: Any) -> str:
        if value is None:
            return "HOLD"

        text = str(value).strip().upper()

        if text in {"BUY", "LONG", "GO_LONG"}:
            return "BUY"
        if text in {"SELL", "SHORT", "GO_SHORT"}:
            return "SELL"
        if text in {"HOLD", "NONE", "SKIP", "WAIT"}:
            return "HOLD"

        return "HOLD"

    @staticmethod
    def _normalize_direction(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip().upper()

        if text in {"BUY", "LONG", "GO_LONG"}:
            return "LONG"
        if text in {"SELL", "SHORT", "GO_SHORT"}:
            return "SHORT"
        if text in {"HOLD", "NONE", "SKIP", "WAIT"}:
            return None

        return None

    @staticmethod
    def _to_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0

        if confidence < 0.0:
            return 0.0
        if confidence > 1.0:
            return 1.0
        return confidence

    @staticmethod
    def _to_reason(value: Any) -> str:
        if value is None:
            return "No reason provided by strategy."
        text = str(value).strip()
        return text if text else "No reason provided by strategy."

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _resolve_should_trade(explicit_value: Any, action: str, direction: str | None) -> bool:
        if isinstance(explicit_value, bool):
            return explicit_value

        if isinstance(explicit_value, str):
            text = explicit_value.strip().lower()
            if text in {"true", "1", "yes", "y"}:
                return True
            if text in {"false", "0", "no", "n"}:
                return False

        return action in {"BUY", "SELL"} and direction in {"LONG", "SHORT"}

    @staticmethod
    def _is_action_direction_consistent(action: str, direction: str | None) -> bool:
        if action == "BUY" and direction == "LONG":
            return True
        if action == "SELL" and direction == "SHORT":
            return True
        if action == "HOLD":
            return direction is None
        return False

    @staticmethod
    def _is_trade_geometry_valid(evaluation: RuleEvaluation) -> bool:
        if evaluation.entry is None or evaluation.stop_loss is None or evaluation.take_profit is None:
            return False

        if evaluation.direction == "LONG":
            return evaluation.stop_loss < evaluation.entry < evaluation.take_profit

        if evaluation.direction == "SHORT":
            return evaluation.take_profit < evaluation.entry < evaluation.stop_loss

        return False

    @staticmethod
    def _calculate_risk_reward(entry: float, stop_loss: float, take_profit: float) -> float:
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)

        if risk <= 0:
            return 0.0

        return reward / risk