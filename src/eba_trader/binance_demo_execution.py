from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from typing import Any

from .providers import CredentialEnvelope

DEMO_FUTURES_REST = "https://demo-fapi.binance.com"
PROOF_SCHEMA = "binance_demo_execution_proof_v1"
CONFIG_SCHEMA = "binance_demo_execution_probe_config_v1"


@dataclass(frozen=True, slots=True)
class DemoExecutionConfig:
    probe_id: str
    symbol: str
    target_notional_usdt: float
    max_notional_usdt: float

    def validate(self) -> None:
        if not self.probe_id.strip():
            raise ValueError("probe_id is required")
        if not self.symbol or not self.symbol.isalnum() or self.symbol.upper() != self.symbol:
            raise ValueError("symbol must be uppercase alphanumeric")
        for name, value in (
            ("target_notional_usdt", self.target_notional_usdt),
            ("max_notional_usdt", self.max_notional_usdt),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"{name} must be positive and finite")
        if self.target_notional_usdt > self.max_notional_usdt:
            raise ValueError("target_notional_usdt cannot exceed max_notional_usdt")


@dataclass(frozen=True, slots=True)
class RequestResult:
    payload: Any
    latency_ms: float


class BinanceDemoExecutionClient:
    """Hard-locked Binance USD-M Demo client for one-shot execution verification.

    The base URL is not configurable and no live endpoint is present in this module.
    The client has no transfer, withdrawal, leverage, margin-mode or account-setting methods.
    """

    def __init__(self, credentials: CredentialEnvelope) -> None:
        if not credentials.api_key or not credentials.api_secret:
            raise ValueError("Binance Demo API key and secret are required")
        self._api_key = credentials.api_key
        self._api_secret = credentials.api_secret
        self._clock_offset_ms = 0

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        signed: bool = False,
        timeout: float = 12.0,
    ) -> RequestResult:
        query = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "eba-demo-execution-probe/1"}
        if signed:
            query["timestamp"] = str(int(time.time() * 1000) + self._clock_offset_ms)
            query["recvWindow"] = "5000"
            encoded_unsigned = urllib.parse.urlencode(query)
            signature = hmac.new(
                self._api_secret.encode("utf-8"),
                encoded_unsigned.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            query["signature"] = signature
            headers["X-MBX-APIKEY"] = self._api_key
        encoded = urllib.parse.urlencode(query)
        url = f"{DEMO_FUTURES_REST}{path}"
        if encoded:
            url = f"{url}?{encoded}"
        request = urllib.request.Request(url, headers=headers, method=method)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Binance Demo HTTP {exc.code}: {body[:320]}") from exc
        latency_ms = (time.perf_counter() - started) * 1000.0
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Binance Demo returned invalid JSON") from exc
        return RequestResult(payload=payload, latency_ms=latency_ms)

    def sync_clock(self) -> dict[str, float]:
        local_before_ms = time.time() * 1000.0
        result = self._request("GET", "/fapi/v1/time")
        local_after_ms = time.time() * 1000.0
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo time response is invalid")
        server_time = result.payload.get("serverTime")
        if isinstance(server_time, bool) or not isinstance(server_time, (int, float)):
            raise RuntimeError("Binance Demo serverTime is missing")
        local_midpoint = (local_before_ms + local_after_ms) / 2.0
        self._clock_offset_ms = int(float(server_time) - local_midpoint)
        return {
            "serverTimeRttMs": result.latency_ms,
            "clockOffsetMs": float(self._clock_offset_ms),
        }

    def exchange_info(self) -> dict[str, Any]:
        result = self._request("GET", "/fapi/v1/exchangeInfo")
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo exchangeInfo response is invalid")
        return result.payload

    def book_ticker(self, symbol: str) -> tuple[dict[str, Any], float]:
        result = self._request("GET", "/fapi/v1/ticker/bookTicker", params={"symbol": symbol})
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo bookTicker response is invalid")
        return result.payload, result.latency_ms

    def latest_aggregate_trade(self, symbol: str) -> tuple[dict[str, Any], float]:
        result = self._request(
            "GET",
            "/fapi/v1/aggTrades",
            params={"symbol": symbol, "limit": "1"},
        )
        if not isinstance(result.payload, list) or len(result.payload) != 1:
            raise RuntimeError("Binance Demo aggTrades response is invalid")
        row = result.payload[0]
        if not isinstance(row, dict):
            raise RuntimeError("Binance Demo aggregate trade row is invalid")
        return row, result.latency_ms

    def position_mode_hedged(self) -> bool:
        result = self._request("GET", "/fapi/v1/positionSide/dual", signed=True)
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo position mode response is invalid")
        value = result.payload.get("dualSidePosition")
        if not isinstance(value, bool):
            raise RuntimeError("Binance Demo position mode is missing")
        return value

    def position_risk(self, symbol: str) -> list[dict[str, Any]]:
        result = self._request(
            "GET",
            "/fapi/v3/positionRisk",
            params={"symbol": symbol},
            signed=True,
        )
        if not isinstance(result.payload, list):
            raise RuntimeError("Binance Demo positionRisk response is invalid")
        rows = [row for row in result.payload if isinstance(row, dict)]
        if not rows:
            raise RuntimeError("Binance Demo positionRisk returned no rows")
        return rows

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        hedged: bool,
        close_long: bool,
    ) -> RequestResult:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "newOrderRespType": "RESULT",
        }
        if hedged:
            params["positionSide"] = "LONG"
        elif close_long:
            params["reduceOnly"] = "true"
        result = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo order response is invalid")
        return result

    def query_order(self, *, symbol: str, order_id: int) -> RequestResult:
        result = self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": str(order_id)},
            signed=True,
        )
        if not isinstance(result.payload, dict):
            raise RuntimeError("Binance Demo query order response is invalid")
        return result


def _decimal(value: Any, *, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except Exception as exc:  # Decimal raises multiple input-specific exceptions
        raise RuntimeError(f"invalid decimal value for {label}") from exc
    if not number.is_finite():
        raise RuntimeError(f"non-finite decimal value for {label}")
    return number


def _symbol_filters(exchange_info: dict[str, Any], symbol: str) -> dict[str, dict[str, Any]]:
    symbols = exchange_info.get("symbols")
    if not isinstance(symbols, list):
        raise RuntimeError("Binance Demo exchangeInfo symbols are missing")
    row = next(
        (
            item
            for item in symbols
            if isinstance(item, dict) and str(item.get("symbol")) == symbol
        ),
        None,
    )
    if not isinstance(row, dict):
        raise RuntimeError(f"Binance Demo symbol is unavailable: {symbol}")
    if row.get("status") != "TRADING":
        raise RuntimeError(f"Binance Demo symbol is not trading: {symbol}")
    filters_raw = row.get("filters")
    if not isinstance(filters_raw, list):
        raise RuntimeError("Binance Demo symbol filters are missing")
    filters: dict[str, dict[str, Any]] = {}
    for item in filters_raw:
        if isinstance(item, dict) and isinstance(item.get("filterType"), str):
            filters[str(item["filterType"])] = item
    return filters


def _format_quantity(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _quantity_for_notional(
    *,
    filters: dict[str, dict[str, Any]],
    mid_price: Decimal,
    target_notional: Decimal,
    max_notional: Decimal,
) -> tuple[Decimal, Decimal]:
    lot = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
    if not isinstance(lot, dict):
        raise RuntimeError("Binance Demo market lot-size filter is missing")
    min_qty = _decimal(lot.get("minQty", "0"), label="minQty")
    max_qty = _decimal(lot.get("maxQty", "0"), label="maxQty")
    step_size = _decimal(lot.get("stepSize", "0"), label="stepSize")
    if min_qty <= 0 or max_qty <= 0 or step_size <= 0:
        raise RuntimeError("Binance Demo quantity filter is invalid")

    min_notional = Decimal("0")
    notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
    if isinstance(notional_filter, dict):
        raw = notional_filter.get("notional") or notional_filter.get("minNotional") or "0"
        min_notional = _decimal(raw, label="minNotional")

    floor_notional = max(
        target_notional,
        min_notional * Decimal("1.05"),
        min_qty * mid_price * Decimal("1.05"),
    )
    raw_qty = floor_notional / mid_price
    steps = (raw_qty / step_size).to_integral_value(rounding=ROUND_CEILING)
    quantity = max(min_qty, steps * step_size)
    if quantity > max_qty:
        raise RuntimeError("required Binance Demo quantity exceeds maxQty")
    effective_notional = quantity * mid_price
    if effective_notional > max_notional:
        raise RuntimeError(
            "required Binance Demo order exceeds configured max_notional_usdt"
        )
    return quantity, effective_notional


def _position_amount(rows: list[dict[str, Any]], *, hedged: bool) -> Decimal:
    if hedged:
        relevant = [row for row in rows if str(row.get("positionSide")) == "LONG"]
    else:
        relevant = [row for row in rows if str(row.get("positionSide")) in {"BOTH", ""}]
    if not relevant:
        raise RuntimeError("expected Binance Demo position row is missing")
    return sum(
        (_decimal(row.get("positionAmt", "0"), label="positionAmt") for row in relevant),
        Decimal("0"),
    )


def _filled_order_payload(client: BinanceDemoExecutionClient, symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "")
    if status == "FILLED":
        return payload
    order_id = payload.get("orderId")
    if isinstance(order_id, bool) or not isinstance(order_id, int):
        raise RuntimeError("Binance Demo order did not return a usable orderId")
    deadline = time.monotonic() + 5.0
    latest = payload
    while time.monotonic() < deadline:
        queried = client.query_order(symbol=symbol, order_id=order_id)
        if not isinstance(queried.payload, dict):
            raise RuntimeError("Binance Demo queried order payload is invalid")
        latest = queried.payload
        status = str(latest.get("status") or "")
        if status == "FILLED":
            return latest
        if status in {"CANCELED", "EXPIRED", "REJECTED"}:
            raise RuntimeError(f"Binance Demo market order ended as {status}")
        time.sleep(0.1)
    raise RuntimeError(f"Binance Demo market order did not fill, last status={status or 'UNKNOWN'}")


def _fill_price(payload: dict[str, Any]) -> Decimal:
    price = _decimal(payload.get("avgPrice", "0"), label="avgPrice")
    if price <= 0:
        price = _decimal(payload.get("price", "0"), label="price")
    if price <= 0:
        raise RuntimeError("Binance Demo filled order has no positive fill price")
    return price


def _executed_quantity(payload: dict[str, Any]) -> Decimal:
    quantity = _decimal(payload.get("executedQty", "0"), label="executedQty")
    if quantity <= 0:
        raise RuntimeError("Binance Demo filled order has no executed quantity")
    return quantity


def _slippage_bps(fill_price: Decimal, reference_price: Decimal, *, side: str) -> float:
    if reference_price <= 0:
        raise RuntimeError("reference price must be positive")
    signed = (fill_price - reference_price) / reference_price
    if side == "SELL":
        signed = -signed
    return float(signed * Decimal("10000"))


def run_demo_execution_probe(
    *,
    credentials: CredentialEnvelope,
    config: DemoExecutionConfig,
    client: BinanceDemoExecutionClient | None = None,
) -> dict[str, Any]:
    config.validate()
    active_client = client or BinanceDemoExecutionClient(credentials)
    symbol = config.symbol
    target_notional = Decimal(str(config.target_notional_usdt))
    max_notional = Decimal(str(config.max_notional_usdt))
    order_submitted = False
    open_filled = False
    emergency_close_attempted = False
    roundtrip_started = time.perf_counter()

    clock = active_client.sync_clock()
    exchange_info = active_client.exchange_info()
    filters = _symbol_filters(exchange_info, symbol)
    hedged = active_client.position_mode_hedged()
    before_rows = active_client.position_risk(symbol)
    before_position = _position_amount(before_rows, hedged=hedged)
    if before_position != 0:
        raise RuntimeError(
            "Binance Demo execution probe requires a zero pre-existing position for the symbol"
        )

    book, book_rtt_ms = active_client.book_ticker(symbol)
    bid = _decimal(book.get("bidPrice", "0"), label="bidPrice")
    ask = _decimal(book.get("askPrice", "0"), label="askPrice")
    if bid <= 0 or ask <= 0 or ask < bid:
        raise RuntimeError("Binance Demo book ticker prices are invalid")
    open_reference = (bid + ask) / Decimal("2")
    quantity, effective_notional = _quantity_for_notional(
        filters=filters,
        mid_price=open_reference,
        target_notional=target_notional,
        max_notional=max_notional,
    )
    quantity_text = _format_quantity(quantity)

    latest_trade, trade_rtt_ms = active_client.latest_aggregate_trade(symbol)
    trade_time = latest_trade.get("T")
    market_data_age_ms: float | None = None
    if not isinstance(trade_time, bool) and isinstance(trade_time, (int, float)):
        market_data_age_ms = max(0.0, time.time() * 1000.0 - float(trade_time))

    open_result: RequestResult | None = None
    close_result: RequestResult | None = None
    open_payload: dict[str, Any] | None = None
    close_payload: dict[str, Any] | None = None
    executed_quantity = Decimal("0")

    try:
        open_result = active_client.place_market_order(
            symbol=symbol,
            side="BUY",
            quantity=quantity_text,
            hedged=hedged,
            close_long=False,
        )
        order_submitted = True
        open_payload = _filled_order_payload(active_client, symbol, open_result.payload)
        executed_quantity = _executed_quantity(open_payload)
        open_filled = True
        open_fill_price = _fill_price(open_payload)

        close_book, close_book_rtt_ms = active_client.book_ticker(symbol)
        close_bid = _decimal(close_book.get("bidPrice", "0"), label="closeBidPrice")
        close_ask = _decimal(close_book.get("askPrice", "0"), label="closeAskPrice")
        if close_bid <= 0 or close_ask <= 0 or close_ask < close_bid:
            raise RuntimeError("Binance Demo close reference prices are invalid")
        close_reference = (close_bid + close_ask) / Decimal("2")

        close_result = active_client.place_market_order(
            symbol=symbol,
            side="SELL",
            quantity=_format_quantity(executed_quantity),
            hedged=hedged,
            close_long=True,
        )
        close_payload = _filled_order_payload(active_client, symbol, close_result.payload)
        close_fill_price = _fill_price(close_payload)
        after_rows = active_client.position_risk(symbol)
        after_position = _position_amount(after_rows, hedged=hedged)
        position_flat = abs(after_position) <= Decimal("0.000000000001")
        if not position_flat:
            raise RuntimeError("Binance Demo execution probe did not return the position to zero")

        roundtrip_ms = (time.perf_counter() - roundtrip_started) * 1000.0
        return {
            "schema": PROOF_SCHEMA,
            "probeId": config.probe_id,
            "phase": "COMPLETE",
            "passed": True,
            "environment": "demo",
            "venue": "Binance USD-M Futures Demo",
            "endpointHost": "demo-fapi.binance.com",
            "symbol": symbol,
            "positionMode": "hedge" if hedged else "one-way",
            "quantity": _format_quantity(executed_quantity),
            "targetNotionalUsdt": config.target_notional_usdt,
            "effectiveNotionalUsdt": float(effective_notional),
            "maxNotionalUsdt": config.max_notional_usdt,
            "orderSubmitted": True,
            "openFilled": True,
            "closeFilled": True,
            "prePositionZero": True,
            "postPositionZero": True,
            "latency": {
                **clock,
                "bookTickerRttMs": book_rtt_ms,
                "latestTradeRttMs": trade_rtt_ms,
                "marketDataAgeMs": market_data_age_ms,
                "openOrderAckMs": open_result.latency_ms,
                "closeReferenceRttMs": close_book_rtt_ms,
                "closeOrderAckMs": close_result.latency_ms,
                "roundTripMs": roundtrip_ms,
            },
            "fills": {
                "openAvgPrice": float(open_fill_price),
                "closeAvgPrice": float(close_fill_price),
                "openSlippageBps": _slippage_bps(open_fill_price, open_reference, side="BUY"),
                "closeSlippageBps": _slippage_bps(close_fill_price, close_reference, side="SELL"),
            },
            "realMoneyUsed": False,
            "liveExecutionAllowed": False,
        }
    except Exception:
        if open_filled and executed_quantity > 0:
            emergency_close_attempted = True
            try:
                active_client.place_market_order(
                    symbol=symbol,
                    side="SELL",
                    quantity=_format_quantity(executed_quantity),
                    hedged=hedged,
                    close_long=True,
                )
            except Exception:
                pass
        raise
    finally:
        _ = order_submitted, emergency_close_attempted, close_payload
