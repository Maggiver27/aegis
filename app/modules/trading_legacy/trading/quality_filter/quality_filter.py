from __future__ import annotations

from typing import Any


class QualityFilter:
    """
    Strict validation layer between strategy/rule output and RiskManager.

    Purpose:
    - reject incomplete or malformed candidates early
    - stop bad upstream normalization from reaching risk sizing
    - support both dict-based and attribute-based signal objects
    """

    VALID_DIRECTIONS = {"BUY", "SELL", "LONG", "SHORT"}

    def __init__(self) -> None:
        pass

    def evaluate(self, signal: Any) -> tuple[bool, str]:
        """
        Returns:
            (True, "") if signal is valid
            (False, reason) if signal must be rejected
        """

        if signal is None:
            return False, "signal_is_none"

        symbol = self._read_value(signal, "symbol")
        timeframe = self._read_value(signal, "timeframe")
        direction = self._read_value(signal, "direction")
        entry = self._read_value(signal, "entry")
        stop_loss = self._read_value(signal, "stop_loss")
        take_profit = self._read_value(signal, "take_profit")

        if not self._is_valid_text_value(symbol):
            return False, "invalid_symbol"

        if not self._is_valid_text_value(timeframe):
            return False, "invalid_timeframe"

        if not self._is_valid_direction(direction):
            return False, "invalid_direction"

        if entry is None:
            return False, "missing_entry"

        if stop_loss is None:
            return False, "missing_stop_loss"

        if take_profit is None:
            return False, "missing_take_profit"

        return True, ""

    @staticmethod
    def _read_value(signal: Any, field_name: str) -> Any:
        """
        Read value from either:
        - dict-like signal
        - attribute-based signal object
        """

        if isinstance(signal, dict):
            return signal.get(field_name)

        return getattr(signal, field_name, None)

    @staticmethod
    def _is_valid_text_value(value: Any) -> bool:
        if value is None:
            return False

        if not isinstance(value, str):
            return False

        cleaned = value.strip()
        if not cleaned:
            return False

        if cleaned.upper() == "UNKNOWN":
            return False

        return True

    def _is_valid_direction(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False

        cleaned = value.strip().upper()
        if not cleaned:
            return False

        return cleaned in self.VALID_DIRECTIONS