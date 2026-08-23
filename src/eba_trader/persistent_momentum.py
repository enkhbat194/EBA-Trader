from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .momentum_engine import (
    MARGIN_USD,
    MAX_RISK_USD,
    MomentumPaperEngine,
    MomentumPosition,
    MomentumTrade,
)
from .persistence import DEFAULT_DB_PATH, PositionRecord, TradeLedger
from .providers import CredentialEnvelope

STRATEGY_NAME = "FAST_MOMENTUM"


def _iso_from_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).isoformat()


def _ms_from_iso(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def ledger_from_env() -> TradeLedger:
    path = Path(os.getenv("EBA_LEDGER_DB", str(DEFAULT_DB_PATH)))
    return TradeLedger(path)


class PersistentMomentumPaperEngine(MomentumPaperEngine):
    """Fast Momentum simulator backed by the shared SQLite TradeLedger.

    The parent engine remains responsible for signal/risk/P&L calculations.
    This class makes its paper state restart-safe and auditable. It never sends
    Binance orders and does not change exchange leverage.
    """

    def __init__(
        self,
        *,
        ledger: TradeLedger,
        margin_usd: float = MARGIN_USD,
        max_risk_usd: float = MAX_RISK_USD,
    ) -> None:
        super().__init__(margin_usd=margin_usd, max_risk_usd=max_risk_usd)
        self._ledger = ledger
        self._restored_sessions: set[str] = set()

    def step(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        allow_entry: bool = True,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        self._restore_session(session_key)
        state = super().step(
            session_key,
            credentials,
            allow_entry=allow_entry,
            now_ms=now_ms,
        )
        if state.get("event") == "MOMENTUM_MARK":
            with self._lock:
                position = self._positions.get(session_key)
                if position is not None:
                    self._persist_open_position(session_key, position)
                    self._ledger.append_event(
                        "FAST_MOMENTUM_MARK",
                        position_id=position.position_id,
                        payload={
                            "sessionKey": session_key,
                            "markPrice": position.mark_price,
                            "grossPnlUsd": position.unrealized_gross_usd,
                            "netPnlUsd": position.unrealized_net_usd,
                        },
                    )
        return state

    def state(self, session_key: str) -> dict[str, Any]:
        self._restore_session(session_key)
        return super().state(session_key)

    def close(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        reason: str = "MANUAL_MOMENTUM_CLOSE",
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        self._restore_session(session_key)
        return super().close(
            session_key,
            credentials,
            reason=reason,
            now_ms=now_ms,
        )

    def _open_locked(
        self,
        session_key: str,
        signal: dict[str, Any],
        fee_rate: float,
        bid: float,
        ask: float,
        now_ms: int,
    ) -> tuple[bool, str]:
        opened, reason = super()._open_locked(
            session_key,
            signal,
            fee_rate,
            bid,
            ask,
            now_ms,
        )
        if opened:
            position = self._positions[session_key]
            self._persist_open_position(session_key, position, signal=signal)
            self._ledger.append_event(
                "FAST_MOMENTUM_OPEN",
                position_id=position.position_id,
                payload={
                    "sessionKey": session_key,
                    "side": position.side,
                    "entryPrice": position.entry_price,
                    "takeProfit": position.take_profit_price,
                    "stopLoss": position.stop_price,
                    "marginUsd": position.margin_usd,
                    "notionalUsd": position.notional_usd,
                    "effectiveLeverage": position.effective_leverage,
                    "score": position.score,
                    "signal": dict(signal),
                },
            )
        return opened, reason

    def _close_locked(
        self,
        session_key: str,
        position: MomentumPosition,
        exit_price: float,
        now_ms: int,
        reason: str,
    ) -> None:
        super()._close_locked(session_key, position, exit_price, now_ms, reason)
        self._ledger.upsert_position(
            PositionRecord(
                position_id=position.position_id,
                symbol=position.symbol,
                side=position.side,
                status="CLOSED",
                entry_price=position.entry_price,
                quantity=position.quantity,
                leverage=position.effective_leverage,
                take_profit=position.take_profit_price,
                stop_loss=position.stop_price,
                opened_at=_iso_from_ms(position.entry_time_ms),
                closed_at=_iso_from_ms(now_ms),
                exit_price=exit_price,
                realized_pnl=position.unrealized_net_usd,
                strategy=STRATEGY_NAME,
                metadata=self._metadata_for_position(
                    session_key,
                    position,
                    exit_reason=reason,
                    exit_time_ms=now_ms,
                ),
            )
        )
        self._ledger.append_event(
            "FAST_MOMENTUM_CLOSE",
            position_id=position.position_id,
            payload={
                "sessionKey": session_key,
                "exitReason": reason,
                "exitPrice": exit_price,
                "grossPnlUsd": position.unrealized_gross_usd,
                "netPnlUsd": position.unrealized_net_usd,
                "entryFeeUsd": position.entry_fee_usd,
                "exitFeeUsd": position.exit_fee_usd,
            },
        )

    def _persist_open_position(
        self,
        session_key: str,
        position: MomentumPosition,
        *,
        signal: dict[str, Any] | None = None,
    ) -> None:
        metadata = self._metadata_for_position(session_key, position)
        if signal is not None:
            metadata["entrySignal"] = dict(signal)
        else:
            previous = self._ledger.get_position(position.position_id)
            if previous and isinstance(previous.get("metadata"), dict):
                entry_signal = previous["metadata"].get("entrySignal")
                if entry_signal is not None:
                    metadata["entrySignal"] = entry_signal
        self._ledger.upsert_position(
            PositionRecord(
                position_id=position.position_id,
                symbol=position.symbol,
                side=position.side,
                status="OPEN",
                entry_price=position.entry_price,
                quantity=position.quantity,
                leverage=position.effective_leverage,
                take_profit=position.take_profit_price,
                stop_loss=position.stop_price,
                opened_at=_iso_from_ms(position.entry_time_ms),
                strategy=STRATEGY_NAME,
                metadata=metadata,
            )
        )

    @staticmethod
    def _metadata_for_position(
        session_key: str,
        position: MomentumPosition,
        *,
        exit_reason: str | None = None,
        exit_time_ms: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sessionKey": session_key,
            "marginUsd": position.margin_usd,
            "notionalUsd": position.notional_usd,
            "leverageCap": position.leverage_cap,
            "effectiveLeverage": position.effective_leverage,
            "feeRate": position.fee_rate,
            "entryFeeUsd": position.entry_fee_usd,
            "exitFeeUsd": position.exit_fee_usd,
            "score": position.score,
            "markPrice": position.mark_price,
            "grossPnlUsd": position.unrealized_gross_usd,
            "netPnlUsd": position.unrealized_net_usd,
        }
        if exit_reason is not None:
            payload["exitReason"] = exit_reason
        if exit_time_ms is not None:
            payload["exitTimeMs"] = exit_time_ms
        return payload

    def _restore_session(self, session_key: str) -> None:
        with self._lock:
            if session_key in self._restored_sessions:
                return
            self._restored_sessions.add(session_key)

            rows = [
                row
                for row in self._ledger.list_positions()
                if row.get("strategy") == STRATEGY_NAME
                and isinstance(row.get("metadata"), dict)
                and row["metadata"].get("sessionKey") == session_key
            ]

            history: list[MomentumTrade] = []
            open_position: MomentumPosition | None = None
            markers: list[dict[str, Any]] = []

            for row in reversed(rows):
                metadata = row.get("metadata") or {}
                entry_time_ms = _ms_from_iso(row.get("opened_at"))
                if entry_time_ms is None:
                    continue
                entry_marker = {
                    "time": entry_time_ms // 1000,
                    "price": float(row["entry_price"]),
                    "kind": "BUY" if row["side"] == "LONG" else "SELL",
                    "label": f"MOM {row['side']} {float(row.get('leverage') or 1.0):.1f}x",
                }
                markers.append(entry_marker)

                if row.get("status") == "OPEN" and open_position is None:
                    open_position = MomentumPosition(
                        position_id=str(row["position_id"]),
                        symbol=str(row["symbol"]),
                        side=str(row["side"]),
                        entry_time_ms=entry_time_ms,
                        entry_price=float(row["entry_price"]),
                        quantity=float(row["quantity"]),
                        notional_usd=float(metadata.get("notionalUsd") or 0.0),
                        margin_usd=float(metadata.get("marginUsd") or self._margin_usd),
                        leverage_cap=int(metadata.get("leverageCap") or round(float(row.get("leverage") or 1.0))),
                        effective_leverage=float(metadata.get("effectiveLeverage") or row.get("leverage") or 1.0),
                        stop_price=float(row.get("stop_loss") or 0.0),
                        take_profit_price=float(row.get("take_profit") or 0.0),
                        fee_rate=float(metadata.get("feeRate") or 0.0),
                        entry_fee_usd=float(metadata.get("entryFeeUsd") or 0.0),
                        score=int(metadata.get("score") or 0),
                        unrealized_gross_usd=float(metadata.get("grossPnlUsd") or 0.0),
                        unrealized_net_usd=float(metadata.get("netPnlUsd") or 0.0),
                        mark_price=(
                            float(metadata["markPrice"])
                            if metadata.get("markPrice") is not None
                            else None
                        ),
                        exit_fee_usd=float(metadata.get("exitFeeUsd") or 0.0),
                    )
                    continue

                if row.get("status") != "CLOSED" or row.get("exit_price") is None:
                    continue
                exit_time_ms = _ms_from_iso(row.get("closed_at")) or int(metadata.get("exitTimeMs") or 0)
                if exit_time_ms <= 0:
                    continue
                trade = MomentumTrade(
                    position_id=str(row["position_id"]),
                    symbol=str(row["symbol"]),
                    side=str(row["side"]),
                    entry_time_ms=entry_time_ms,
                    exit_time_ms=exit_time_ms,
                    entry_price=float(row["entry_price"]),
                    exit_price=float(row["exit_price"]),
                    quantity=float(row["quantity"]),
                    notional_usd=float(metadata.get("notionalUsd") or 0.0),
                    margin_usd=float(metadata.get("marginUsd") or self._margin_usd),
                    effective_leverage=float(metadata.get("effectiveLeverage") or row.get("leverage") or 1.0),
                    entry_fee_usd=float(metadata.get("entryFeeUsd") or 0.0),
                    exit_fee_usd=float(metadata.get("exitFeeUsd") or 0.0),
                    gross_pnl_usd=float(metadata.get("grossPnlUsd") or 0.0),
                    net_pnl_usd=float(row.get("realized_pnl") or 0.0),
                    exit_reason=str(metadata.get("exitReason") or "RECOVERED_CLOSE"),
                    score=int(metadata.get("score") or 0),
                )
                history.append(trade)
                markers.append(
                    {
                        "time": exit_time_ms // 1000,
                        "price": float(row["exit_price"]),
                        "kind": "EXIT",
                        "label": "MOM EXIT",
                    }
                )

            if open_position is not None:
                self._positions[session_key] = open_position
            if history:
                self._history[session_key] = history[-100:]
            if markers:
                self._markers[session_key] = markers[-200:]
