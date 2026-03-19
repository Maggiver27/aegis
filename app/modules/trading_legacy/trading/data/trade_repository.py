from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from app.trading.models.trade import Trade, TradeStatus


class TradeRepository:
    """
    Repozytorium odpowiedzialne za przechowywanie i odczytywanie obiektów Trade.

    Zasada architektoniczna:
    - pipeline pracuje na obiektach domenowych Trade
    - repozytorium konwertuje Trade <-> dict tylko na granicy persistence
    - SQLite przechowuje dane w formie prymitywów + JSON dla metadata

    Uwaga:
    - na obecnym etapie save() działa jako UPSERT przez INSERT OR REPLACE
    - domena używa trade_id, a warstwa bazy przechowuje to pole jako id
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    pair TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    lot_size REAL NOT NULL,
                    risk_percent REAL NOT NULL,
                    risk_amount REAL NOT NULL,
                    stop_distance_price REAL NOT NULL,
                    stop_distance_pips REAL NOT NULL,
                    strategy_name TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sizing_mode TEXT NOT NULL,
                    pip_size REAL NOT NULL,
                    pip_value_per_standard_lot REAL NOT NULL,
                    scan_score REAL,
                    scan_score_ratio REAL,
                    scan_rating_factors TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    opened_at TEXT,
                    closed_at TEXT,
                    exit_price REAL,
                    pnl REAL
                )
                """
            )

            self._ensure_column(
                conn,
                "trades",
                "scan_score",
                "REAL",
            )
            self._ensure_column(
                conn,
                "trades",
                "scan_score_ratio",
                "REAL",
            )
            self._ensure_column(
                conn,
                "trades",
                "scan_rating_factors",
                "TEXT",
            )

            conn.commit()

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        existing_columns = {row["name"] for row in rows}
        if column_name in existing_columns:
            return

        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )

    def save(self, trade: Trade) -> None:
        """
        Zapisuje obiekt domenowy Trade do bazy.

        Na tym etapie projektu używamy INSERT OR REPLACE jako świadomego UPSERT.
        """
        data = self._trade_to_storage_dict(trade)
        self._validate_required_fields(data)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trades (
                    id,
                    pair,
                    direction,
                    entry,
                    stop_loss,
                    take_profit,
                    lot_size,
                    risk_percent,
                    risk_amount,
                    stop_distance_price,
                    stop_distance_pips,
                    strategy_name,
                    timeframe,
                    signal_type,
                    source,
                    created_at,
                    sizing_mode,
                    pip_size,
                    pip_value_per_standard_lot,
                    scan_score,
                    scan_score_ratio,
                    scan_rating_factors,
                    status,
                    metadata,
                    opened_at,
                    closed_at,
                    exit_price,
                    pnl
                )
                VALUES (
                    :id,
                    :pair,
                    :direction,
                    :entry,
                    :stop_loss,
                    :take_profit,
                    :lot_size,
                    :risk_percent,
                    :risk_amount,
                    :stop_distance_price,
                    :stop_distance_pips,
                    :strategy_name,
                    :timeframe,
                    :signal_type,
                    :source,
                    :created_at,
                    :sizing_mode,
                    :pip_size,
                    :pip_value_per_standard_lot,
                    :scan_score,
                    :scan_score_ratio,
                    :scan_rating_factors,
                    :status,
                    :metadata,
                    :opened_at,
                    :closed_at,
                    :exit_price,
                    :pnl
                )
                """,
                data,
            )
            conn.commit()

    def get(self, trade_id: str) -> Trade | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM trades
                WHERE id = ?
                """,
                (trade_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_trade(row)

    def list_all(self) -> list[Trade]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM trades
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

        return [self._row_to_trade(row) for row in rows]

    def delete(self, trade_id: str) -> bool:
        """
        Usuwa trade po jego trade_id / id.

        Zwraca:
        - True, jeśli rekord został usunięty
        - False, jeśli rekord o podanym id nie istniał
        """
        if not isinstance(trade_id, str) or not trade_id.strip():
            raise ValueError("trade_id must be a non-empty string")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM trades
                WHERE id = ?
                """,
                (trade_id.strip(),),
            )
            conn.commit()

        return cursor.rowcount > 0

    def cleanup_prepared_duplicates(self) -> int:
        """
        Usuwa starsze duplikaty PREPARED, zostawiając tylko najnowszy rekord
        dla tego samego setupu.

        Duplikat definiowany jest przez:
        - pair
        - direction
        - timeframe
        - strategy_name
        - entry
        - stop_loss
        - take_profit
        - lot_size
        """
        trades = self.list_all()

        kept_keys: set[tuple[Any, ...]] = set()
        ids_to_delete: list[str] = []

        for trade in trades:
            if trade.status != TradeStatus.PREPARED:
                continue

            key = (
                trade.pair,
                trade.direction,
                trade.timeframe,
                trade.strategy_name,
                trade.entry,
                trade.stop_loss,
                trade.take_profit,
                trade.lot_size,
            )

            trade_id = getattr(trade, "trade_id", None)
            if not trade_id or not str(trade_id).strip():
                continue

            if key in kept_keys:
                ids_to_delete.append(str(trade_id))
            else:
                kept_keys.add(key)

        if not ids_to_delete:
            return 0

        placeholders = ",".join("?" for _ in ids_to_delete)

        with self._connect() as conn:
            conn.execute(
                f"DELETE FROM trades WHERE id IN ({placeholders})",
                ids_to_delete,
            )
            conn.commit()

        return len(ids_to_delete)

    def _trade_to_storage_dict(self, trade: Trade) -> dict[str, Any]:
        raw = trade.to_dict()

        storage_id = raw.get("id") or raw.get("trade_id")
        if not storage_id:
            storage_id = str(uuid.uuid4())

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        scan_rating_factors = raw.get("scan_rating_factors", {})
        if not isinstance(scan_rating_factors, dict):
            scan_rating_factors = {}

        normalized_scan_rating_factors: dict[str, float] = {}
        for key, value in scan_rating_factors.items():
            key_text = str(key).strip()
            if not key_text:
                continue

            numeric_value = self._to_float_or_none(value)
            if numeric_value is None:
                continue

            normalized_scan_rating_factors[key_text] = numeric_value

        status_value = raw.get("status")
        if isinstance(status_value, TradeStatus):
            status_value = status_value.value
        elif status_value is None:
            status_value = ""

        data: dict[str, Any] = {
            "id": storage_id,
            "pair": raw.get("pair", ""),
            "direction": raw.get("direction", ""),
            "entry": raw.get("entry"),
            "stop_loss": raw.get("stop_loss"),
            "take_profit": raw.get("take_profit"),
            "lot_size": raw.get("lot_size"),
            "risk_percent": raw.get("risk_percent"),
            "risk_amount": raw.get("risk_amount"),
            "stop_distance_price": raw.get("stop_distance_price"),
            "stop_distance_pips": raw.get("stop_distance_pips"),
            "strategy_name": raw.get("strategy_name", ""),
            "timeframe": raw.get("timeframe", ""),
            "signal_type": raw.get("signal_type", ""),
            "source": raw.get("source", ""),
            "created_at": raw.get("created_at", ""),
            "sizing_mode": raw.get("sizing_mode", ""),
            "pip_size": raw.get("pip_size"),
            "pip_value_per_standard_lot": raw.get("pip_value_per_standard_lot"),
            "scan_score": self._to_float_or_none(raw.get("scan_score")),
            "scan_score_ratio": self._to_float_or_none(raw.get("scan_score_ratio")),
            "scan_rating_factors": json.dumps(
                normalized_scan_rating_factors,
                ensure_ascii=False,
            ),
            "status": status_value,
            "metadata": json.dumps(metadata, ensure_ascii=False),
            "opened_at": raw.get("opened_at"),
            "closed_at": raw.get("closed_at"),
            "exit_price": raw.get("exit_price"),
            "pnl": raw.get("pnl"),
        }

        return data

    def _validate_required_fields(self, data: dict[str, Any]) -> None:
        required_not_none = [
            "id",
            "entry",
            "stop_loss",
            "take_profit",
            "lot_size",
            "risk_percent",
            "risk_amount",
            "stop_distance_price",
            "stop_distance_pips",
            "pip_size",
            "pip_value_per_standard_lot",
        ]

        missing_not_none = [
            field for field in required_not_none if data.get(field) is None
        ]
        if missing_not_none:
            raise ValueError(
                "TradeRepository.save() missing required numeric fields: "
                + ", ".join(missing_not_none)
            )

        required_not_blank = [
            "id",
            "pair",
            "direction",
            "strategy_name",
            "timeframe",
            "signal_type",
            "source",
            "created_at",
            "sizing_mode",
            "status",
        ]

        missing_not_blank = [
            field
            for field in required_not_blank
            if not isinstance(data.get(field), str) or not data[field].strip()
        ]
        if missing_not_blank:
            raise ValueError(
                "TradeRepository.save() missing required text fields: "
                + ", ".join(missing_not_blank)
            )

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        metadata = self._deserialize_json_dict(row["metadata"])
        scan_rating_factors = self._deserialize_json_dict(
            row["scan_rating_factors"]
        )

        data = {
            "id": row["id"],
            "trade_id": row["id"],
            "pair": row["pair"],
            "direction": row["direction"],
            "entry": row["entry"],
            "stop_loss": row["stop_loss"],
            "take_profit": row["take_profit"],
            "lot_size": row["lot_size"],
            "risk_percent": row["risk_percent"],
            "risk_amount": row["risk_amount"],
            "stop_distance_price": row["stop_distance_price"],
            "stop_distance_pips": row["stop_distance_pips"],
            "strategy_name": row["strategy_name"],
            "timeframe": row["timeframe"],
            "signal_type": row["signal_type"],
            "source": row["source"],
            "created_at": row["created_at"],
            "sizing_mode": row["sizing_mode"],
            "pip_size": row["pip_size"],
            "pip_value_per_standard_lot": row["pip_value_per_standard_lot"],
            "scan_score": row["scan_score"],
            "scan_score_ratio": row["scan_score_ratio"],
            "scan_rating_factors": scan_rating_factors,
            "status": row["status"],
            "metadata": metadata,
            "opened_at": row["opened_at"],
            "closed_at": row["closed_at"],
            "exit_price": row["exit_price"],
            "pnl": row["pnl"],
        }

        return Trade.from_dict(data)

    def _deserialize_json_dict(self, value: str | None) -> dict[str, Any]:
        if not value:
            return {}

        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None