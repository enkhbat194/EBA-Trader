from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from .m18_fee_policy import (
    DEFAULT_DEPTH_LIMIT,
    DEFAULT_QUANTITY_BTC,
    FUTURES_BASE_URL,
    FUTURES_COMMISSION_ENDPOINT,
    FUTURES_DEPTH_ENDPOINT,
    FUTURES_EXCHANGE_INFO_ENDPOINT,
    M18ExecutionPolicy,
    RECV_WINDOW_MS,
    SPOT_BASE_URL,
    SPOT_COMMISSION_ENDPOINT,
    SPOT_DEPTH_ENDPOINT,
    SPOT_SYMBOL,
)

Side = Literal["BUY", "SELL"]
LiquidityRole = Literal["maker", "taker"]


class PairDecision(StrEnum):
    NO_TRADE = "NO_TRADE"
    PAPER_CANDIDATE = "PAPER_CANDIDATE"


@dataclass(frozen=True, slots=True)
class CommissionComponent:
    maker: float
    taker: float
    buyer: float = 0.0
    seller: float = 0.0

    def __post_init__(self) -> None:
        for value in (self.maker, self.taker, self.buyer, self.seller):
            if value < 0:
                raise ValueError("commission rates must be non-negative")

    def rate(self, side: Side, role: LiquidityRole) -> float:
        role_rate = self.maker if role == "maker" else self.taker
        side_rate = self.buyer if side == "BUY" else self.seller
        return role_rate + side_rate


@dataclass(frozen=True, slots=True)
class SpotCommissionSnapshot:
    symbol: str
    standard: CommissionComponent
    special: CommissionComponent
    tax: CommissionComponent
    discount_enabled: bool
    standard_discount_multiplier: float

    def effective_rate(self, side: Side, role: LiquidityRole = "taker") -> float:
        standard = self.standard.rate(side, role)
        if self.discount_enabled:
            standard *= self.standard_discount_multiplier
        return standard + self.special.rate(side, role) + self.tax.rate(side, role)


@dataclass(frozen=True, slots=True)
class FuturesCommissionSnapshot:
    symbol: str
    maker: float
    taker: float
    rpi: float | None = None

    def __post_init__(self) -> None:
        for value in (self.maker, self.taker):
            if value < 0:
                raise ValueError("futures commission rates must be non-negative")
        if self.rpi is not None and self.rpi < 0:
            raise ValueError("RPI commission rate must be non-negative")


@dataclass(frozen=True, slots=True)
class BookLevel:
    price: float
    quantity: float

    def __post_init__(self) -> None:
        if self.price <= 0 or self.quantity <= 0:
            raise ValueError("order-book price and quantity must be positive")


@dataclass(frozen=True, slots=True)
class BookSnapshot:
    symbol: str
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]
    received_at_ms: int


@dataclass(frozen=True, slots=True)
class FillEstimate:
    quantity: float
    vwap: float
    notional: float
    worst_price: float
    levels_used: int


@dataclass(frozen=True, slots=True)
class FeeAwarePairEstimate:
    decision: PairDecision
    reason_codes: tuple[str, ...]
    spot_symbol: str
    futures_symbol: str
    quantity_btc: float
    spot_entry_vwap: float | None = None
    futures_entry_vwap: float | None = None
    fully_funded_capital_usd: float | None = None
    gross_convergence_usd: float | None = None
    gross_edge_bps: float | None = None
    entry_fee_usd: float | None = None
    reserved_exit_fee_usd: float | None = None
    reserved_exit_slippage_usd: float | None = None
    safety_buffer_usd: float | None = None
    screening_net_usd: float | None = None
    screening_net_edge_bps: float | None = None
    spot_buy_taker_rate: float | None = None
    spot_sell_taker_rate: float | None = None
    futures_taker_rate: float | None = None
    live_execution_allowed: bool = False


def _float(value: Any, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric field {field}") from exc
    if parsed < 0:
        raise ValueError(f"negative numeric field {field}")
    return parsed


def _component(payload: dict[str, Any], name: str) -> CommissionComponent:
    return CommissionComponent(
        maker=_float(payload.get("maker", 0.0), field=f"{name}.maker"),
        taker=_float(payload.get("taker", 0.0), field=f"{name}.taker"),
        buyer=_float(payload.get("buyer", 0.0), field=f"{name}.buyer"),
        seller=_float(payload.get("seller", 0.0), field=f"{name}.seller"),
    )


def parse_spot_commission(payload: dict[str, Any]) -> SpotCommissionSnapshot:
    symbol = str(payload.get("symbol", ""))
    if not symbol:
        raise ValueError("spot commission payload missing symbol")

    discount = payload.get("discount") or {}
    enabled = bool(discount.get("enabledForAccount")) and bool(
        discount.get("enabledForSymbol")
    )
    multiplier = _float(discount.get("discount", 1.0), field="discount.discount")
    if multiplier > 1.0:
        raise ValueError("spot commission discount multiplier must be <= 1")

    return SpotCommissionSnapshot(
        symbol=symbol,
        standard=_component(payload.get("standardCommission") or {}, "standardCommission"),
        special=_component(payload.get("specialCommission") or {}, "specialCommission"),
        tax=_component(payload.get("taxCommission") or {}, "taxCommission"),
        discount_enabled=enabled,
        standard_discount_multiplier=multiplier if enabled else 1.0,
    )


def parse_futures_commission(payload: dict[str, Any]) -> FuturesCommissionSnapshot:
    symbol = str(payload.get("symbol", ""))
    if not symbol:
        raise ValueError("futures commission payload missing symbol")
    rpi_raw = payload.get("rpiCommissionRate")
    return FuturesCommissionSnapshot(
        symbol=symbol,
        maker=_float(payload.get("makerCommissionRate"), field="makerCommissionRate"),
        taker=_float(payload.get("takerCommissionRate"), field="takerCommissionRate"),
        rpi=_float(rpi_raw, field="rpiCommissionRate") if rpi_raw is not None else None,
    )


def parse_book(payload: dict[str, Any], *, symbol: str, received_at_ms: int) -> BookSnapshot:
    def levels(name: str) -> tuple[BookLevel, ...]:
        raw_levels = payload.get(name)
        if not isinstance(raw_levels, list):
            raise ValueError(f"order-book payload missing {name}")
        parsed: list[BookLevel] = []
        for raw in raw_levels:
            if not isinstance(raw, list | tuple) or len(raw) < 2:
                raise ValueError(f"invalid order-book level in {name}")
            price = float(raw[0])
            quantity = float(raw[1])
            if price <= 0 or quantity <= 0:
                continue
            parsed.append(BookLevel(price=price, quantity=quantity))
        return tuple(parsed)

    bids = levels("bids")
    asks = levels("asks")
    if not bids or not asks:
        raise ValueError("order book must contain positive bid and ask liquidity")
    return BookSnapshot(symbol=symbol, bids=bids, asks=asks, received_at_ms=received_at_ms)


def _simulate_fill(levels: tuple[BookLevel, ...], quantity: float) -> FillEstimate | None:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    remaining = quantity
    notional = 0.0
    used = 0
    worst = 0.0
    for level in levels:
        take = min(remaining, level.quantity)
        if take <= 0:
            continue
        notional += take * level.price
        remaining -= take
        used += 1
        worst = level.price
        if remaining <= 1e-12:
            break
    if remaining > 1e-12:
        return None
    return FillEstimate(
        quantity=quantity,
        vwap=notional / quantity,
        notional=notional,
        worst_price=worst,
        levels_used=used,
    )


def simulate_buy(book: BookSnapshot, quantity: float) -> FillEstimate | None:
    return _simulate_fill(book.asks, quantity)


def simulate_sell(book: BookSnapshot, quantity: float) -> FillEstimate | None:
    return _simulate_fill(book.bids, quantity)


def evaluate_cash_carry_snapshot(
    *,
    spot_book: BookSnapshot,
    futures_book: BookSnapshot,
    spot_commission: SpotCommissionSnapshot,
    futures_commission: FuturesCommissionSnapshot,
    quantity_btc: float,
    now_ms: int,
    policy: M18ExecutionPolicy | None = None,
) -> FeeAwarePairEstimate:
    policy = policy or M18ExecutionPolicy()
    base = {
        "spot_symbol": spot_book.symbol,
        "futures_symbol": futures_book.symbol,
        "quantity_btc": quantity_btc,
        "live_execution_allowed": False,
    }
    if quantity_btc <= 0:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=("INVALID_QUANTITY",),
            **base,
        )
    if spot_commission.symbol != spot_book.symbol:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=("SPOT_COMMISSION_SYMBOL_MISMATCH",),
            **base,
        )
    if futures_commission.symbol != futures_book.symbol:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=("FUTURES_COMMISSION_SYMBOL_MISMATCH",),
            **base,
        )

    stale: list[str] = []
    if now_ms < spot_book.received_at_ms or now_ms - spot_book.received_at_ms > policy.max_quote_age_ms:
        stale.append("STALE_SPOT_BOOK")
    if (
        now_ms < futures_book.received_at_ms
        or now_ms - futures_book.received_at_ms > policy.max_quote_age_ms
    ):
        stale.append("STALE_FUTURES_BOOK")
    if stale:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=tuple(stale),
            **base,
        )

    spot_fill = simulate_buy(spot_book, quantity_btc)
    futures_fill = simulate_sell(futures_book, quantity_btc)
    depth_reasons: list[str] = []
    if spot_fill is None:
        depth_reasons.append("INSUFFICIENT_SPOT_ASK_DEPTH")
    if futures_fill is None:
        depth_reasons.append("INSUFFICIENT_FUTURES_BID_DEPTH")
    if depth_reasons:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=tuple(depth_reasons),
            **base,
        )

    assert spot_fill is not None
    assert futures_fill is not None
    capital = spot_fill.notional + futures_fill.notional
    if capital <= 0:
        return FeeAwarePairEstimate(
            decision=PairDecision.NO_TRADE,
            reason_codes=("INVALID_CAPITAL_DENOMINATOR",),
            **base,
        )

    gross = quantity_btc * (futures_fill.vwap - spot_fill.vwap)
    spot_buy_rate = spot_commission.effective_rate("BUY", "taker")
    spot_sell_rate = spot_commission.effective_rate("SELL", "taker")
    futures_taker_rate = futures_commission.taker

    entry_fee = spot_fill.notional * spot_buy_rate + futures_fill.notional * futures_taker_rate
    conservative_exit_price = max(spot_fill.vwap, futures_fill.vwap)
    exit_notional = quantity_btc * conservative_exit_price
    reserved_exit_fee = exit_notional * (spot_sell_rate + futures_taker_rate)
    reserved_exit_slippage = (
        exit_notional
        * 2.0
        * policy.exit_slippage_reserve_bps_per_leg
        / 10_000.0
    )
    safety_buffer = capital * policy.safety_buffer_bps / 10_000.0
    screening_net = gross - entry_fee - reserved_exit_fee - reserved_exit_slippage - safety_buffer
    gross_edge_bps = gross / capital * 10_000.0
    net_edge_bps = screening_net / capital * 10_000.0

    reasons: list[str] = []
    if gross <= 0:
        reasons.append("NON_POSITIVE_EXECUTABLE_PREMIUM")
    if net_edge_bps < policy.min_screening_net_edge_bps:
        reasons.append("NET_EDGE_BELOW_MINIMUM")
    decision = PairDecision.PAPER_CANDIDATE if not reasons else PairDecision.NO_TRADE
    if decision is PairDecision.PAPER_CANDIDATE:
        reasons.append("FEE_AWARE_PAPER_GATE_PASSED")

    return FeeAwarePairEstimate(
        decision=decision,
        reason_codes=tuple(reasons),
        spot_symbol=spot_book.symbol,
        futures_symbol=futures_book.symbol,
        quantity_btc=quantity_btc,
        spot_entry_vwap=spot_fill.vwap,
        futures_entry_vwap=futures_fill.vwap,
        fully_funded_capital_usd=capital,
        gross_convergence_usd=gross,
        gross_edge_bps=gross_edge_bps,
        entry_fee_usd=entry_fee,
        reserved_exit_fee_usd=reserved_exit_fee,
        reserved_exit_slippage_usd=reserved_exit_slippage,
        safety_buffer_usd=safety_buffer,
        screening_net_usd=screening_net,
        screening_net_edge_bps=net_edge_bps,
        spot_buy_taker_rate=spot_buy_rate,
        spot_sell_taker_rate=spot_sell_rate,
        futures_taker_rate=futures_taker_rate,
        live_execution_allowed=False,
    )


def select_nearest_btcusdt_delivery_symbol(payload: dict[str, Any], *, now_ms: int) -> str:
    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        raise ValueError("futures exchangeInfo missing symbols")
    candidates: list[tuple[int, str]] = []
    for item in symbols:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", ""))
        if not symbol.startswith("BTCUSDT_"):
            continue
        if item.get("baseAsset") != "BTC" or item.get("quoteAsset") != "USDT":
            continue
        if item.get("status") != "TRADING":
            continue
        try:
            delivery = int(item.get("deliveryDate"))
        except (TypeError, ValueError):
            continue
        if delivery <= now_ms:
            continue
        candidates.append((delivery, symbol))
    if not candidates:
        raise RuntimeError("no active future BTCUSDT delivery contract found")
    candidates.sort()
    return candidates[0][1]


class BinanceReadOnlyClient:
    """Minimal signed/public Binance REST client with no trading methods."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> BinanceReadOnlyClient:
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        if not api_key or not api_secret:
            raise RuntimeError(
                "M18 read-only commission snapshot requires BINANCE_API_KEY and "
                "BINANCE_API_SECRET environment variables"
            )
        return cls(api_key=api_key, api_secret=api_secret)

    def _get_json(self, url: str, *, authenticated: bool) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["X-MBX-APIKEY"] = self._api_key
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("unexpected Binance JSON response")
        return payload

    def _public_get(self, base_url: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = f"{base_url}{endpoint}"
        if query:
            url = f"{url}?{query}"
        return self._get_json(url, authenticated=False)

    def _signed_get(self, base_url: str, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        signed_params = dict(params)
        signed_params.setdefault("recvWindow", RECV_WINDOW_MS)
        signed_params.setdefault("timestamp", int(time.time() * 1000))
        query = urllib.parse.urlencode(signed_params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return self._get_json(
            f"{base_url}{endpoint}?{query}&signature={signature}",
            authenticated=True,
        )

    def spot_commission(self, symbol: str = SPOT_SYMBOL) -> SpotCommissionSnapshot:
        payload = self._signed_get(
            SPOT_BASE_URL,
            SPOT_COMMISSION_ENDPOINT,
            {"symbol": symbol},
        )
        return parse_spot_commission(payload)

    def futures_commission(self, symbol: str) -> FuturesCommissionSnapshot:
        payload = self._signed_get(
            FUTURES_BASE_URL,
            FUTURES_COMMISSION_ENDPOINT,
            {"symbol": symbol},
        )
        return parse_futures_commission(payload)

    def spot_book(self, symbol: str = SPOT_SYMBOL, *, limit: int = DEFAULT_DEPTH_LIMIT) -> BookSnapshot:
        payload = self._public_get(
            SPOT_BASE_URL,
            SPOT_DEPTH_ENDPOINT,
            {"symbol": symbol, "limit": limit},
        )
        return parse_book(payload, symbol=symbol, received_at_ms=int(time.time() * 1000))

    def futures_book(self, symbol: str, *, limit: int = DEFAULT_DEPTH_LIMIT) -> BookSnapshot:
        payload = self._public_get(
            FUTURES_BASE_URL,
            FUTURES_DEPTH_ENDPOINT,
            {"symbol": symbol, "limit": limit},
        )
        return parse_book(payload, symbol=symbol, received_at_ms=int(time.time() * 1000))

    def futures_exchange_info(self) -> dict[str, Any]:
        return self._public_get(FUTURES_BASE_URL, FUTURES_EXCHANGE_INFO_ENDPOINT, {})


def run_read_only_snapshot(
    *,
    futures_symbol: str | None = None,
    quantity_btc: float = DEFAULT_QUANTITY_BTC,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    client = BinanceReadOnlyClient.from_env()
    now_ms = int(time.time() * 1000)
    symbol = futures_symbol or select_nearest_btcusdt_delivery_symbol(
        client.futures_exchange_info(),
        now_ms=now_ms,
    )
    policy = M18ExecutionPolicy()
    spot_commission = client.spot_commission(SPOT_SYMBOL)
    futures_commission = client.futures_commission(symbol)
    spot_book = client.spot_book(SPOT_SYMBOL, limit=policy.depth_limit)
    futures_book = client.futures_book(symbol, limit=policy.depth_limit)
    evaluation_time_ms = int(time.time() * 1000)
    estimate = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=spot_commission,
        futures_commission=futures_commission,
        quantity_btc=quantity_btc,
        now_ms=evaluation_time_ms,
        policy=policy,
    )
    result = {
        "mode": "READ_ONLY_NO_ORDER_ENDPOINTS",
        "decision": estimate.decision.value,
        "estimate": asdict(estimate),
        "policy": asdict(policy),
        "futures_symbol": symbol,
        "snapshot_time_ms": evaluation_time_ms,
        "live_execution_allowed": False,
        "oos_2025": "LOCKED_NOT_ACCESSED",
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="M18 read-only fee-aware cash-carry snapshot")
    parser.add_argument("--futures-symbol")
    parser.add_argument("--quantity-btc", type=float, default=DEFAULT_QUANTITY_BTC)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_read_only_snapshot(
        futures_symbol=args.futures_symbol,
        quantity_btc=args.quantity_btc,
        output_path=args.output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
