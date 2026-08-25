from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("/var/lib/eba-trader/eba_trader.db")


@dataclass(frozen=True)
class PositionRecord:
    position_id: str
    symbol: str
    side: str
    status: str
    entry_price: float
    quantity: float
    leverage: float = 1.0
    take_profit: float | None = None
    stop_loss: float | None = None
    opened_at: str | None = None
    closed_at: str | None = None
    exit_price: float | None = None
    realized_pnl: float | None = None
    strategy: str | None = None
    metadata: dict[str, Any] | None = None


class TradeLedger:
    """Small SQLite-backed state store for restart-safe paper/live metadata."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    leverage REAL NOT NULL DEFAULT 1.0,
                    take_profit REAL,
                    stop_loss REAL,
                    opened_at TEXT,
                    closed_at TEXT,
                    exit_price REAL,
                    realized_pnl REAL,
                    strategy TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_positions_status
                    ON positions(status);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    position_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_events_position_id
                    ON events(position_id);
                """
            )

    def upsert_position(self, record: PositionRecord) -> None:
        values = asdict(record)
        metadata_json = json.dumps(values.pop("metadata") or {}, separators=(",", ":"))
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO positions (
                    position_id, symbol, side, status, entry_price, quantity,
                    leverage, take_profit, stop_loss, opened_at, closed_at,
                    exit_price, realized_pnl, strategy, metadata_json
                ) VALUES (
                    :position_id, :symbol, :side, :status, :entry_price, :quantity,
                    :leverage, :take_profit, :stop_loss, :opened_at, :closed_at,
                    :exit_price, :realized_pnl, :strategy, :metadata_json
                )
                ON CONFLICT(position_id) DO UPDATE SET
                    symbol=excluded.symbol,
                    side=excluded.side,
                    status=excluded.status,
                    entry_price=excluded.entry_price,
                    quantity=excluded.quantity,
                    leverage=excluded.leverage,
                    take_profit=excluded.take_profit,
                    stop_loss=excluded.stop_loss,
                    opened_at=excluded.opened_at,
                    closed_at=excluded.closed_at,
                    exit_price=excluded.exit_price,
                    realized_pnl=excluded.realized_pnl,
                    strategy=excluded.strategy,
                    metadata_json=excluded.metadata_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                {**values, "metadata_json": metadata_json},
            )

    def append_event(
        self,
        event_type: str,
        *,
        position_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO events(event_type, position_id, payload_json) VALUES (?, ?, ?)",
                (
                    event_type,
                    position_id,
                    json.dumps(payload or {}, separators=(",", ":")),
                ),
            )
            return int(cursor.lastrowid)

    def list_positions(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM positions"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY COALESCE(opened_at, updated_at) DESC"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_position(row) for row in rows]

    def get_position(self, position_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM positions WHERE position_id = ?", (position_id,)
            ).fetchone()
        return self._row_to_position(row) if row else None

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "position_id": row["position_id"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload_json"] or "{}"),
            }
            for row in rows
        ]

    @staticmethod
    def _row_to_position(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
        return data
