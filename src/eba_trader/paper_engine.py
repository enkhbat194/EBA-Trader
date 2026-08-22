from __future__ import annotations

import secrets
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any

MAX_PAPER_CAPITAL_USD = 10_000.0
DELIVERY_EXIT_BUFFER_MS = 15 * 60 * 1000


@dataclass(slots=True)
class PaperPosition:
    position_id: str
    provider: str
    spot_symbol: str
    futures_symbol: str
    quantity_btc: float
    entry_time_ms: int
    spot_entry_vwap: float
    futures_entry_vwap: float
    entry_fee_usd: float
    capital_usd: float
    delivery_time_ms: int | None
    unrealized_gross_usd: float = 0.0
    unrealized_net_usd: float = 0.0
    spot_exit_vwap: float | None = None
    futures_exit_vwap: float | None = None
    exit_fee_usd: float = 0.0


@dataclass(slots=True)
class PaperTrade:
    position_id: str
    provider: str
    spot_symbol: str
    futures_symbol: str
    quantity_btc: float
    entry_time_ms: int
    exit_time_ms: int
    spot_entry_vwap: float
    spot_exit_vwap: float
    futures_entry_vwap: float
    futures_exit_vwap: float
    entry_fee_usd: float
    exit_fee_usd: float
    gross_pnl_usd: float
    net_pnl_usd: float
    exit_reason: str


class PaperExecutionEngine:
    """Operational paper-only harness for the existing M18 candidate gate.

    It never places exchange orders. A single paired position may be opened per
    Binance Demo session only after the existing `PAPER_CANDIDATE` gate passes.
    Mark-to-market uses executable close-side VWAP and current Demo commissions.
    This is engineering validation, not a new profitability claim.
    """

    def __init__(self, *, max_capital_usd: float = MAX_PAPER_CAPITAL_USD) -> None:
        if max_capital_usd <= 0:
            raise ValueError("max_capital_usd must be positive")
        self._max_capital_usd = max_capital_usd
        self._positions: dict[str, PaperPosition] = {}
        self._history: dict[str, list[PaperTrade]] = {}
        self._markers: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def step(
        self,
        session_key: str,
        snapshot: dict[str, Any],
        *,
        allow_entry: bool = True,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        if not session_key:
            raise ValueError("session_key is required")
        now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        with self._lock:
            position = self._positions.get(session_key)
            event = "NO_ACTION"
            reason = "NO_PAPER_CANDIDATE" if allow_entry else "ENTRY_SCANNER_STOPPED"

            if position is not None:
                mark_reason = self._mark_position(position, snapshot)
                reason = mark_reason
                delivery = position.delivery_time_ms
                if (
                    delivery is not None
                    and now_ms >= delivery - DELIVERY_EXIT_BUFFER_MS
                    and position.spot_exit_vwap is not None
                    and position.futures_exit_vwap is not None
                ):
                    self._close_locked(session_key, position, now_ms, "DELIVERY_SAFETY_EXIT")
                    event = "PAPER_EXIT"
                    reason = "DELIVERY_SAFETY_EXIT"
                else:
                    event = "PAPER_MARK"
            elif allow_entry and snapshot.get("decision") == "PAPER_CANDIDATE":
                position, reason = self._open_candidate(snapshot, now_ms)
                if position is not None:
                    self._positions[session_key] = position
                    self._markers.setdefault(session_key, []).append(
                        {
                            "time": now_ms // 1000,
                            "price": position.spot_entry_vwap,
                            "kind": "BUY",
                            "label": "PAPER ENTRY",
                        }
                    )
                    event = "PAPER_ENTRY"

            return self._state_locked(session_key, event=event, reason=reason)

    def close(
        self,
        session_key: str,
        snapshot: dict[str, Any],
        *,
        reason: str = "MANUAL_PAPER_CLOSE",
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        with self._lock:
            position = self._positions.get(session_key)
            if position is None:
                return self._state_locked(
                    session_key,
                    event="NO_ACTION",
                    reason="NO_OPEN_PAPER_POSITION",
                )
            mark_reason = self._mark_position(position, snapshot)
            if position.spot_exit_vwap is None or position.futures_exit_vwap is None:
                return self._state_locked(session_key, event="NO_ACTION", reason=mark_reason)
            self._close_locked(session_key, position, now_ms, reason)
            return self._state_locked(session_key, event="PAPER_EXIT", reason=reason)

    def state(self, session_key: str) -> dict[str, Any]:
        with self._lock:
            return self._state_locked(session_key, event="STATE", reason="OK")

    def clear(self, session_key: str) -> None:
        with self._lock:
            self._positions.pop(session_key, None)
            self._history.pop(session_key, None)
            self._markers.pop(session_key, None)

    def markers(self, session_key: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._markers.get(session_key, [])]

    def _open_candidate(
        self,
        snapshot: dict[str, Any],
        now_ms: int,
    ) -> tuple[PaperPosition | None, str]:
        estimate = snapshot.get("estimate")
        if not isinstance(estimate, dict):
            return None, "MISSING_ENTRY_ESTIMATE"
        try:
            quantity = float(estimate["quantity_btc"])
            spot_entry = float(estimate["spot_entry_vwap"])
            futures_entry = float(estimate["futures_entry_vwap"])
            entry_fee = float(estimate["entry_fee_usd"])
            capital = float(estimate["fully_funded_capital_usd"])
        except (KeyError, TypeError, ValueError):
            return None, "INVALID_ENTRY_ESTIMATE"
        if quantity <= 0 or spot_entry <= 0 or futures_entry <= 0 or capital <= 0:
            return None, "INVALID_ENTRY_ESTIMATE"
        if capital > self._max_capital_usd:
            return None, "PAPER_CAPITAL_LIMIT"
        futures_symbol = str(
            snapshot.get("futuresSymbol") or estimate.get("futures_symbol") or ""
        )
        if not futures_symbol:
            return None, "MISSING_FUTURES_SYMBOL"
        delivery_raw = snapshot.get("futuresDeliveryTimeMs")
        delivery = int(delivery_raw) if delivery_raw is not None else None
        return (
            PaperPosition(
                position_id=secrets.token_hex(8),
                provider="binance",
                spot_symbol=str(estimate.get("spot_symbol") or "BTCUSDT"),
                futures_symbol=futures_symbol,
                quantity_btc=quantity,
                entry_time_ms=now_ms,
                spot_entry_vwap=spot_entry,
                futures_entry_vwap=futures_entry,
                entry_fee_usd=max(0.0, entry_fee),
                capital_usd=capital,
                delivery_time_ms=delivery,
            ),
            "PAPER_CANDIDATE_OPENED",
        )

    def _mark_position(self, position: PaperPosition, snapshot: dict[str, Any]) -> str:
        if snapshot.get("futuresSymbol") != position.futures_symbol:
            return "PAPER_FUTURES_SYMBOL_MISMATCH"
        close_quote = snapshot.get("closeQuote")
        if not isinstance(close_quote, dict):
            return "PAPER_CLOSE_QUOTE_UNAVAILABLE"
        try:
            spot_exit = float(close_quote["spotExitVwap"])
            futures_exit = float(close_quote["futuresExitVwap"])
            exit_fee = float(close_quote["exitFeeUsd"])
        except (KeyError, TypeError, ValueError):
            return "PAPER_CLOSE_QUOTE_INVALID"
        if spot_exit <= 0 or futures_exit <= 0 or exit_fee < 0:
            return "PAPER_CLOSE_QUOTE_INVALID"
        gross = position.quantity_btc * (spot_exit - position.spot_entry_vwap)
        gross += position.quantity_btc * (position.futures_entry_vwap - futures_exit)
        position.spot_exit_vwap = spot_exit
        position.futures_exit_vwap = futures_exit
        position.exit_fee_usd = exit_fee
        position.unrealized_gross_usd = gross
        position.unrealized_net_usd = gross - position.entry_fee_usd - exit_fee
        return "PAPER_MARKED"

    def _close_locked(
        self,
        session_key: str,
        position: PaperPosition,
        now_ms: int,
        reason: str,
    ) -> None:
        assert position.spot_exit_vwap is not None
        assert position.futures_exit_vwap is not None
        trade = PaperTrade(
            position_id=position.position_id,
            provider=position.provider,
            spot_symbol=position.spot_symbol,
            futures_symbol=position.futures_symbol,
            quantity_btc=position.quantity_btc,
            entry_time_ms=position.entry_time_ms,
            exit_time_ms=now_ms,
            spot_entry_vwap=position.spot_entry_vwap,
            spot_exit_vwap=position.spot_exit_vwap,
            futures_entry_vwap=position.futures_entry_vwap,
            futures_exit_vwap=position.futures_exit_vwap,
            entry_fee_usd=position.entry_fee_usd,
            exit_fee_usd=position.exit_fee_usd,
            gross_pnl_usd=position.unrealized_gross_usd,
            net_pnl_usd=position.unrealized_net_usd,
            exit_reason=reason,
        )
        self._history.setdefault(session_key, []).append(trade)
        self._markers.setdefault(session_key, []).append(
            {
                "time": now_ms // 1000,
                "price": position.spot_exit_vwap,
                "kind": "EXIT",
                "label": "PAPER EXIT",
            }
        )
        self._positions.pop(session_key, None)

    def _state_locked(
        self,
        session_key: str,
        *,
        event: str,
        reason: str,
    ) -> dict[str, Any]:
        position = self._positions.get(session_key)
        history = self._history.get(session_key, [])
        realized = sum(item.net_pnl_usd for item in history)
        unrealized = position.unrealized_net_usd if position is not None else 0.0
        return {
            "mode": "PAPER_ONLY",
            "event": event,
            "reason": reason,
            "openPosition": asdict(position) if position is not None else None,
            "history": [asdict(item) for item in history[-100:]],
            "markers": [dict(item) for item in self._markers.get(session_key, [])[-200:]],
            "realizedPnlUsd": realized,
            "unrealizedPnlUsd": unrealized,
            "totalPnlUsd": realized + unrealized,
            "maxPaperCapitalUsd": self._max_capital_usd,
            "liveExecutionAllowed": False,
        }
