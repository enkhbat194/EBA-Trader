from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

from .providers import CredentialEnvelope

DEMO_FUTURES_BASE = "https://demo-fapi.binance.com"
SYMBOL = "BTCUSDT"
MARGIN_USD = 10.0
MAX_RISK_USD = 0.35
MAX_HOLD_MS = 30 * 60 * 1000
MIN_SIGNAL_SCORE = 6
MIN_SCORE_LEAD = 2
FALLBACK_TAKER_FEE_RATE = 0.0005


@dataclass(slots=True)
class MomentumPosition:
    position_id: str
    symbol: str
    side: str
    entry_time_ms: int
    entry_price: float
    quantity: float
    notional_usd: float
    margin_usd: float
    leverage_cap: int
    effective_leverage: float
    stop_price: float
    take_profit_price: float
    fee_rate: float
    entry_fee_usd: float
    score: int
    unrealized_gross_usd: float = 0.0
    unrealized_net_usd: float = 0.0
    mark_price: float | None = None
    exit_fee_usd: float = 0.0


@dataclass(slots=True)
class MomentumTrade:
    position_id: str
    symbol: str
    side: str
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    quantity: float
    notional_usd: float
    margin_usd: float
    effective_leverage: float
    entry_fee_usd: float
    exit_fee_usd: float
    gross_pnl_usd: float
    net_pnl_usd: float
    exit_reason: str
    score: int


def _public_get(path: str, params: dict[str, str]) -> Any:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{DEMO_FUTURES_BASE}{path}?{query}",
        headers={"User-Agent": "EBA-Trader/0.7"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Binance Demo HTTP {exc.code}: {body[:200]}") from exc
    return json.loads(raw)


def _signed_get(
    path: str,
    credentials: CredentialEnvelope,
    params: dict[str, str],
) -> dict[str, Any]:
    if not credentials.api_key or not credentials.api_secret:
        raise RuntimeError("Binance Demo credentials are required")
    query = dict(params)
    query["timestamp"] = str(int(time.time() * 1000))
    query["recvWindow"] = "5000"
    encoded = urllib.parse.urlencode(query)
    signature = hmac.new(
        credentials.api_secret.encode("utf-8"),
        encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    request = urllib.request.Request(
        f"{DEMO_FUTURES_BASE}{path}?{encoded}&signature={signature}",
        headers={"X-MBX-APIKEY": credentials.api_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Binance Demo HTTP {exc.code}: {body[:200]}") from exc
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("unexpected Binance Demo response")
    return payload


def _fetch_candles(interval: str, limit: int = 120) -> list[dict[str, float]]:
    payload = _public_get(
        "/fapi/v1/klines",
        {"symbol": SYMBOL, "interval": interval, "limit": str(limit)},
    )
    if not isinstance(payload, list) or len(payload) < 60:
        raise RuntimeError("insufficient Binance Demo futures candles")
    candles: list[dict[str, float]] = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 6:
            continue
        candles.append(
            {
                "time": float(row[0]) / 1000.0,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    if len(candles) < 60:
        raise RuntimeError("invalid Binance Demo futures candle payload")
    return candles


def _book_ticker() -> tuple[float, float]:
    payload = _public_get("/fapi/v1/ticker/bookTicker", {"symbol": SYMBOL})
    if not isinstance(payload, dict):
        raise RuntimeError("invalid Binance Demo book ticker")
    bid = float(payload.get("bidPrice", 0.0))
    ask = float(payload.get("askPrice", 0.0))
    if bid <= 0 or ask <= 0 or ask < bid:
        raise RuntimeError("invalid Binance Demo bid/ask")
    return bid, ask


def _taker_fee_rate(credentials: CredentialEnvelope) -> float:
    try:
        payload = _signed_get(
            "/fapi/v1/commissionRate",
            credentials,
            {"symbol": SYMBOL},
        )
        value = float(payload.get("takerCommissionRate", 0.0))
        if 0.0 <= value <= 0.01:
            return value
    except Exception:
        pass
    return FALLBACK_TAKER_FEE_RATE


def _ema(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("insufficient EMA values")
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        raise ValueError("insufficient RSI values")
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[:-1], values[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _true_ranges(candles: list[dict[str, float]]) -> list[float]:
    ranges: list[float] = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous_close = candles[index - 1]["close"]
        ranges.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous_close),
                abs(current["low"] - previous_close),
            )
        )
    return ranges


def _atr(candles: list[dict[str, float]], period: int = 14) -> float:
    ranges = _true_ranges(candles)
    if len(ranges) < period:
        raise ValueError("insufficient ATR values")
    value = sum(ranges[:period]) / period
    for item in ranges[period:]:
        value = ((value * (period - 1)) + item) / period
    return value


def _adx(candles: list[dict[str, float]], period: int = 14) -> float:
    if len(candles) < period * 2 + 2:
        raise ValueError("insufficient ADX values")
    trs: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for index in range(1, len(candles)):
        current = candles[index]
        previous = candles[index - 1]
        up = current["high"] - previous["high"]
        down = previous["low"] - current["low"]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous["close"]),
                abs(current["low"] - previous["close"]),
            )
        )
    tr = sum(trs[:period])
    plus = sum(plus_dm[:period])
    minus = sum(minus_dm[:period])
    dx_values: list[float] = []
    for index in range(period, len(trs)):
        tr = tr - (tr / period) + trs[index]
        plus = plus - (plus / period) + plus_dm[index]
        minus = minus - (minus / period) + minus_dm[index]
        if tr <= 0:
            continue
        plus_di = 100.0 * plus / tr
        minus_di = 100.0 * minus / tr
        denominator = plus_di + minus_di
        if denominator > 0:
            dx_values.append(100.0 * abs(plus_di - minus_di) / denominator)
    if len(dx_values) < period:
        return 0.0
    value = sum(dx_values[:period]) / period
    for item in dx_values[period:]:
        value = ((value * (period - 1)) + item) / period
    return value


def analyze_momentum(
    candles_1m: list[dict[str, float]],
    candles_5m: list[dict[str, float]],
) -> dict[str, Any]:
    close_1m = [item["close"] for item in candles_1m]
    close_5m = [item["close"] for item in candles_5m]
    ema20_1m = _ema(close_1m, 20)
    ema50_1m = _ema(close_1m, 50)
    ema20_5m = _ema(close_5m, 20)
    ema50_5m = _ema(close_5m, 50)
    rsi14 = _rsi(close_1m)
    adx14 = _adx(candles_1m)
    atr14 = _atr(candles_1m)
    last = candles_1m[-1]
    previous = candles_1m[-2]
    recent = candles_1m[-4:]
    previous_ten = candles_1m[-11:-1]
    volume_average = sum(item["volume"] for item in candles_1m[-21:-1]) / 20.0
    volume_ratio = last["volume"] / volume_average if volume_average > 0 else 0.0

    higher_structure = all(
        recent[index]["high"] >= recent[index - 1]["high"]
        and recent[index]["low"] >= recent[index - 1]["low"]
        for index in range(1, len(recent))
    )
    lower_structure = all(
        recent[index]["high"] <= recent[index - 1]["high"]
        and recent[index]["low"] <= recent[index - 1]["low"]
        for index in range(1, len(recent))
    )
    previous_high = max(item["high"] for item in previous_ten)
    previous_low = min(item["low"] for item in previous_ten)
    breakout_up = last["close"] > previous_high
    breakout_down = last["close"] < previous_low

    body = abs(last["close"] - last["open"])
    candle_range = max(last["high"] - last["low"], 1e-12)
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]
    fake_up_risk = upper_wick > max(body * 1.8, candle_range * 0.45)
    fake_down_risk = lower_wick > max(body * 1.8, candle_range * 0.45)

    long_score = 0
    short_score = 0
    if ema20_1m > ema50_1m:
        long_score += 1
    elif ema20_1m < ema50_1m:
        short_score += 1
    if ema20_5m > ema50_5m:
        long_score += 2
    elif ema20_5m < ema50_5m:
        short_score += 2
    if higher_structure:
        long_score += 1
    if lower_structure:
        short_score += 1
    if volume_ratio >= 1.15:
        if last["close"] > previous["close"]:
            long_score += 1
        elif last["close"] < previous["close"]:
            short_score += 1
    if adx14 >= 20.0:
        if ema20_1m > ema50_1m:
            long_score += 1
        elif ema20_1m < ema50_1m:
            short_score += 1
    if 52.0 <= rsi14 <= 72.0:
        long_score += 1
    if 28.0 <= rsi14 <= 48.0:
        short_score += 1
    if breakout_up:
        long_score += 1
    if breakout_down:
        short_score += 1
    if rsi14 >= 78.0 or fake_up_risk:
        long_score = max(0, long_score - 1)
    if rsi14 <= 22.0 or fake_down_risk:
        short_score = max(0, short_score - 1)

    side = "NO_TRADE"
    score = max(long_score, short_score)
    if long_score >= MIN_SIGNAL_SCORE and long_score - short_score >= MIN_SCORE_LEAD:
        side = "LONG"
        score = long_score
    elif short_score >= MIN_SIGNAL_SCORE and short_score - long_score >= MIN_SCORE_LEAD:
        side = "SHORT"
        score = short_score

    atr_pct = atr14 / last["close"] if last["close"] > 0 else math.inf
    return {
        "symbol": SYMBOL,
        "decision": side,
        "score": score,
        "longScore": long_score,
        "shortScore": short_score,
        "ema20_1m": ema20_1m,
        "ema50_1m": ema50_1m,
        "ema20_5m": ema20_5m,
        "ema50_5m": ema50_5m,
        "rsi14": rsi14,
        "adx14": adx14,
        "atr14": atr14,
        "atrPct": atr_pct,
        "volumeRatio": volume_ratio,
        "higherHighHigherLow": higher_structure,
        "lowerHighLowerLow": lower_structure,
        "breakoutUp": breakout_up,
        "breakoutDown": breakout_down,
        "fakeBreakoutRisk": fake_up_risk if side == "LONG" else fake_down_risk if side == "SHORT" else (fake_up_risk or fake_down_risk),
        "lastClose": last["close"],
        "liveExecutionAllowed": False,
    }


def _leverage_cap(score: int) -> int:
    if score >= 8:
        return 20
    if score >= 7:
        return 10
    return 5


class MomentumPaperEngine:
    """Deterministic BTCUSDT perpetual momentum simulator.

    This engine is paper-only. It reads Binance Demo market/account fee data and
    never sends orders or changes exchange leverage. The signal rules are an
    engineering prototype and are not a validated profitability claim.
    """

    def __init__(
        self,
        *,
        margin_usd: float = MARGIN_USD,
        max_risk_usd: float = MAX_RISK_USD,
    ) -> None:
        if margin_usd <= 0 or max_risk_usd <= 0:
            raise ValueError("paper margin and risk must be positive")
        self._margin_usd = margin_usd
        self._max_risk_usd = max_risk_usd
        self._positions: dict[str, MomentumPosition] = {}
        self._history: dict[str, list[MomentumTrade]] = {}
        self._markers: dict[str, list[dict[str, Any]]] = {}
        self._last_snapshot: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def step(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        allow_entry: bool = True,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        candles_1m = _fetch_candles("1m")
        candles_5m = _fetch_candles("5m")
        signal = analyze_momentum(candles_1m, candles_5m)
        bid, ask = _book_ticker()
        fee_rate = _taker_fee_rate(credentials)
        signal["bid"] = bid
        signal["ask"] = ask
        signal["spreadBps"] = ((ask - bid) / ((ask + bid) / 2.0)) * 10_000.0
        signal["takerFeeRate"] = fee_rate

        with self._lock:
            self._last_snapshot[session_key] = dict(signal)
            position = self._positions.get(session_key)
            event = "NO_ACTION"
            reason = "NO_QUALIFIED_MOMENTUM_SIGNAL"
            if position is not None:
                exit_price = bid if position.side == "LONG" else ask
                self._mark(position, exit_price)
                exit_reason: str | None = None
                if position.side == "LONG" and exit_price <= position.stop_price:
                    exit_reason = "STOP_LOSS"
                elif position.side == "SHORT" and exit_price >= position.stop_price:
                    exit_reason = "STOP_LOSS"
                elif position.side == "LONG" and exit_price >= position.take_profit_price:
                    exit_reason = "TAKE_PROFIT"
                elif position.side == "SHORT" and exit_price <= position.take_profit_price:
                    exit_reason = "TAKE_PROFIT"
                elif now_ms - position.entry_time_ms >= MAX_HOLD_MS:
                    exit_reason = "MAX_HOLD_EXIT"
                elif signal["decision"] not in {"NO_TRADE", position.side} and signal["score"] >= MIN_SIGNAL_SCORE:
                    exit_reason = "SIGNAL_REVERSAL"
                if exit_reason is not None:
                    self._close_locked(session_key, position, exit_price, now_ms, exit_reason)
                    event = "MOMENTUM_EXIT"
                    reason = exit_reason
                else:
                    event = "MOMENTUM_MARK"
                    reason = "POSITION_MONITORING"
            elif allow_entry and signal["decision"] in {"LONG", "SHORT"}:
                opened, reason = self._open_locked(session_key, signal, fee_rate, bid, ask, now_ms)
                if opened:
                    event = "MOMENTUM_ENTRY"
            elif not allow_entry:
                reason = "ENTRY_SCANNER_STOPPED"
            return self._state_locked(session_key, event=event, reason=reason)

    def state(self, session_key: str) -> dict[str, Any]:
        with self._lock:
            return self._state_locked(session_key, event="STATE", reason="OK")

    def close(
        self,
        session_key: str,
        credentials: CredentialEnvelope,
        *,
        reason: str = "MANUAL_MOMENTUM_CLOSE",
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        bid, ask = _book_ticker()
        with self._lock:
            position = self._positions.get(session_key)
            if position is None:
                return self._state_locked(session_key, event="NO_ACTION", reason="NO_OPEN_MOMENTUM_POSITION")
            exit_price = bid if position.side == "LONG" else ask
            self._mark(position, exit_price)
            self._close_locked(session_key, position, exit_price, now_ms, reason)
            return self._state_locked(session_key, event="MOMENTUM_EXIT", reason=reason)

    def clear(self, session_key: str) -> None:
        with self._lock:
            self._positions.pop(session_key, None)
            self._history.pop(session_key, None)
            self._markers.pop(session_key, None)
            self._last_snapshot.pop(session_key, None)

    def markers(self, session_key: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._markers.get(session_key, [])[-200:]]

    def _open_locked(
        self,
        session_key: str,
        signal: dict[str, Any],
        fee_rate: float,
        bid: float,
        ask: float,
        now_ms: int,
    ) -> tuple[bool, str]:
        side = str(signal["decision"])
        score = int(signal["score"])
        entry = ask if side == "LONG" else bid
        stop_pct = min(0.012, max(0.0025, float(signal["atrPct"]) * 1.2))
        leverage_cap = _leverage_cap(score)
        risk_limited_notional = self._max_risk_usd / stop_pct
        notional = min(self._margin_usd * leverage_cap, risk_limited_notional)
        if notional < 5.0:
            return False, "RISK_BUDGET_TOO_SMALL"
        quantity = notional / entry
        effective_leverage = notional / self._margin_usd
        take_pct = stop_pct * 1.5
        if side == "LONG":
            stop = entry * (1.0 - stop_pct)
            take = entry * (1.0 + take_pct)
        else:
            stop = entry * (1.0 + stop_pct)
            take = entry * (1.0 - take_pct)
        entry_fee = notional * fee_rate
        position = MomentumPosition(
            position_id=secrets.token_hex(8),
            symbol=SYMBOL,
            side=side,
            entry_time_ms=now_ms,
            entry_price=entry,
            quantity=quantity,
            notional_usd=notional,
            margin_usd=self._margin_usd,
            leverage_cap=leverage_cap,
            effective_leverage=effective_leverage,
            stop_price=stop,
            take_profit_price=take,
            fee_rate=fee_rate,
            entry_fee_usd=entry_fee,
            score=score,
        )
        self._positions[session_key] = position
        self._markers.setdefault(session_key, []).append(
            {
                "time": now_ms // 1000,
                "price": entry,
                "kind": "BUY" if side == "LONG" else "SELL",
                "label": f"MOM {side} {effective_leverage:.1f}x",
            }
        )
        return True, "MOMENTUM_SIGNAL_OPENED"

    @staticmethod
    def _mark(position: MomentumPosition, exit_price: float) -> None:
        if position.side == "LONG":
            gross = position.quantity * (exit_price - position.entry_price)
        else:
            gross = position.quantity * (position.entry_price - exit_price)
        exit_fee = position.quantity * exit_price * position.fee_rate
        position.mark_price = exit_price
        position.exit_fee_usd = exit_fee
        position.unrealized_gross_usd = gross
        position.unrealized_net_usd = gross - position.entry_fee_usd - exit_fee

    def _close_locked(
        self,
        session_key: str,
        position: MomentumPosition,
        exit_price: float,
        now_ms: int,
        reason: str,
    ) -> None:
        self._mark(position, exit_price)
        trade = MomentumTrade(
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side,
            entry_time_ms=position.entry_time_ms,
            exit_time_ms=now_ms,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            notional_usd=position.notional_usd,
            margin_usd=position.margin_usd,
            effective_leverage=position.effective_leverage,
            entry_fee_usd=position.entry_fee_usd,
            exit_fee_usd=position.exit_fee_usd,
            gross_pnl_usd=position.unrealized_gross_usd,
            net_pnl_usd=position.unrealized_net_usd,
            exit_reason=reason,
            score=position.score,
        )
        self._history.setdefault(session_key, []).append(trade)
        self._markers.setdefault(session_key, []).append(
            {
                "time": now_ms // 1000,
                "price": exit_price,
                "kind": "EXIT",
                "label": "MOM EXIT",
            }
        )
        self._positions.pop(session_key, None)

    def _state_locked(self, session_key: str, *, event: str, reason: str) -> dict[str, Any]:
        position = self._positions.get(session_key)
        history = self._history.get(session_key, [])
        realized = sum(item.net_pnl_usd for item in history)
        unrealized = position.unrealized_net_usd if position is not None else 0.0
        wins = sum(1 for item in history if item.net_pnl_usd > 0)
        return {
            "mode": "LEVERAGED_MOMENTUM_PAPER_ONLY",
            "event": event,
            "reason": reason,
            "signal": dict(self._last_snapshot.get(session_key, {})),
            "openPosition": asdict(position) if position is not None else None,
            "history": [asdict(item) for item in history[-100:]],
            "markers": [dict(item) for item in self._markers.get(session_key, [])[-200:]],
            "realizedPnlUsd": realized,
            "unrealizedPnlUsd": unrealized,
            "totalPnlUsd": realized + unrealized,
            "tradeCount": len(history),
            "winRate": (wins / len(history)) if history else 0.0,
            "marginUsd": self._margin_usd,
            "maxRiskUsd": self._max_risk_usd,
            "allowedLeverageCaps": [5, 10, 20],
            "liveExecutionAllowed": False,
            "aiSignalAuthority": False,
        }
