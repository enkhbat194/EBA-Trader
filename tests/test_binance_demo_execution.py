from __future__ import annotations

from pathlib import Path

from eba_trader.binance_demo_execution import (
    DEMO_FUTURES_REST,
    BinanceDemoExecutionClient,
    DemoExecutionConfig,
    RequestResult,
    _fill_price,
    run_demo_execution_probe,
)
from eba_trader.providers import CredentialEnvelope


class FakeDemoClient:
    exchange_now_ms = 1_000_100.0

    def __init__(
        self,
        *,
        pre_position: str = "0",
        min_qty: str = "0.001",
        price: str = "100000",
        available_balance: str = "10000",
        hedged: bool = False,
    ) -> None:
        self.pre_position = pre_position
        self.min_qty = min_qty
        self.price = price
        self.available_balance = available_balance
        self.hedged = hedged
        self.orders: list[dict[str, object]] = []
        self.closed = False

    def sync_clock(self) -> dict[str, float]:
        return {"serverTimeRttMs": 20.0, "clockOffsetMs": 2.0}

    def exchange_info(self) -> dict[str, object]:
        return {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "status": "TRADING",
                    "filters": [
                        {
                            "filterType": "MARKET_LOT_SIZE",
                            "minQty": self.min_qty,
                            "maxQty": "1000",
                            "stepSize": self.min_qty,
                        },
                        {"filterType": "MIN_NOTIONAL", "notional": "5"},
                    ],
                }
            ]
        }

    def account(self) -> dict[str, object]:
        return {"availableBalance": self.available_balance}

    def position_mode_hedged(self) -> bool:
        return self.hedged

    def position_risk(self, symbol: str) -> list[dict[str, object]]:
        assert symbol == "BTCUSDT"
        amount = "0" if self.closed else self.pre_position
        return [
            {
                "symbol": symbol,
                "positionSide": "LONG" if self.hedged else "BOTH",
                "positionAmt": amount,
            }
        ]

    def book_ticker(self, symbol: str) -> tuple[dict[str, object], float]:
        assert symbol == "BTCUSDT"
        price = float(self.price)
        return {"bidPrice": str(price - 1), "askPrice": str(price + 1)}, 15.0

    def latest_aggregate_trade(self, symbol: str) -> tuple[dict[str, object], float]:
        assert symbol == "BTCUSDT"
        return {"T": 1_000_000}, 12.0

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        hedged: bool,
        close_long: bool,
    ) -> RequestResult:
        self.orders.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "hedged": hedged,
                "close_long": close_long,
            }
        )
        if side == "SELL":
            self.closed = True
        payload = {
            "orderId": len(self.orders),
            "status": "FILLED",
            "executedQty": quantity,
            "avgPrice": self.price,
        }
        return RequestResult(payload=payload, latency_ms=25.0 if side == "BUY" else 30.0)

    def query_order(self, *, symbol: str, order_id: int) -> RequestResult:
        raise AssertionError("filled fake orders should not require query_order")


def _config(*, max_notional: float = 250.0) -> DemoExecutionConfig:
    return DemoExecutionConfig(
        probe_id="test-probe-v1",
        symbol="BTCUSDT",
        target_notional_usdt=25.0,
        max_notional_usdt=max_notional,
    )


def test_demo_execution_module_is_hard_locked_to_demo_host() -> None:
    source = Path("src/eba_trader/binance_demo_execution.py").read_text(encoding="utf-8")

    assert DEMO_FUTURES_REST == "https://demo-fapi.binance.com"
    assert "https://fapi.binance.com" not in source
    assert "https://api.binance.com" not in source
    assert "withdraw" in source.lower()  # documentation explicitly states it is absent
    assert "change_leverage" not in source
    assert "transfer(" not in source


def test_successful_probe_opens_and_closes_demo_position_and_reports_latency() -> None:
    client = FakeDemoClient()
    result = run_demo_execution_probe(
        credentials=CredentialEnvelope(api_key="demo", api_secret="secret"),
        config=_config(),
        client=client,  # type: ignore[arg-type]
    )

    assert result["phase"] == "COMPLETE"
    assert result["passed"] is True
    assert result["environment"] == "demo"
    assert result["endpointHost"] == "demo-fapi.binance.com"
    assert result["realMoneyUsed"] is False
    assert result["liveExecutionAllowed"] is False
    assert result["prePositionZero"] is True
    assert result["postPositionZero"] is True
    assert result["availableBalanceUsdtBefore"] == 10000.0
    assert result["effectiveNotionalUsdt"] <= 250.0
    assert result["latency"]["openOrderAckMs"] == 25.0
    assert result["latency"]["closeOrderAckMs"] == 30.0
    assert result["latency"]["marketDataAgeMs"] == 100.0
    assert [order["side"] for order in client.orders] == ["BUY", "SELL"]
    assert client.orders[1]["close_long"] is True


def test_probe_fails_closed_before_order_when_existing_position_is_nonzero() -> None:
    client = FakeDemoClient(pre_position="0.001")
    result = run_demo_execution_probe(
        credentials=CredentialEnvelope(api_key="demo", api_secret="secret"),
        config=_config(),
        client=client,  # type: ignore[arg-type]
    )

    assert result["phase"] == "FAILED"
    assert result["passed"] is False
    assert result["orderSubmissionAttempted"] is False
    assert result["positionMayRemainOpen"] is False
    assert client.orders == []


def test_probe_refuses_required_quantity_above_predeclared_notional_cap() -> None:
    client = FakeDemoClient(min_qty="0.01")
    result = run_demo_execution_probe(
        credentials=CredentialEnvelope(api_key="demo", api_secret="secret"),
        config=_config(max_notional=250.0),
        client=client,  # type: ignore[arg-type]
    )

    assert result["phase"] == "FAILED"
    assert result["passed"] is False
    assert result["orderSubmissionAttempted"] is False
    assert "max_notional_usdt" in result["errorSummary"]
    assert client.orders == []


def test_probe_refuses_insufficient_demo_balance_before_order() -> None:
    client = FakeDemoClient(available_balance="50")
    result = run_demo_execution_probe(
        credentials=CredentialEnvelope(api_key="demo", api_secret="secret"),
        config=_config(),
        client=client,  # type: ignore[arg-type]
    )

    assert result["phase"] == "FAILED"
    assert result["orderSubmissionAttempted"] is False
    assert "available USDT balance" in result["errorSummary"]
    assert client.orders == []


def test_real_client_exposes_only_demo_endpoint_configuration() -> None:
    client = BinanceDemoExecutionClient(
        CredentialEnvelope(api_key="demo", api_secret="secret")
    )
    assert client.exchange_now_ms > 0


def test_fill_price_falls_back_to_cum_quote_when_binance_avg_price_is_zero() -> None:
    payload = {
        "status": "FILLED",
        "avgPrice": "0",
        "price": "0",
        "executedQty": "0.0007",
        "cumQuote": "54.25119",
    }

    assert float(_fill_price(payload)) == 77501.7


class ZeroPriceDemoClient(FakeDemoClient):
    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        hedged: bool,
        close_long: bool,
    ) -> RequestResult:
        self.orders.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "hedged": hedged,
                "close_long": close_long,
            }
        )
        if side == "SELL":
            self.closed = True
        return RequestResult(
            payload={
                "orderId": len(self.orders),
                "status": "FILLED",
                "executedQty": quantity,
                "avgPrice": "0",
                "price": "0",
                "cumQuote": "0",
            },
            latency_ms=25.0 if side == "BUY" else 30.0,
        )

    def query_order(self, *, symbol: str, order_id: int) -> RequestResult:
        order = self.orders[order_id - 1]
        return RequestResult(
            payload={
                "orderId": order_id,
                "status": "FILLED",
                "executedQty": order["quantity"],
                "avgPrice": "0",
                "price": "0",
                "cumQuote": "0",
            },
            latency_ms=11.0,
        )

    def account_trades(self, *, symbol: str, order_id: int) -> RequestResult:
        order = self.orders[order_id - 1]
        return RequestResult(
            payload=[
                {
                    "orderId": order_id,
                    "price": self.price,
                    "qty": order["quantity"],
                }
            ],
            latency_ms=13.0,
        )


def test_probe_resolves_zero_price_filled_orders_from_user_trades() -> None:
    client = ZeroPriceDemoClient()
    result = run_demo_execution_probe(
        credentials=CredentialEnvelope(api_key="demo", api_secret="secret"),
        config=_config(),
        client=client,  # type: ignore[arg-type]
    )

    assert result["phase"] == "COMPLETE"
    assert result["passed"] is True
    assert result["openFilled"] is True
    assert result["closeFilled"] is True
    assert result["postPositionZero"] is True
    assert result["fills"]["openAvgPrice"] == 100000.0
    assert result["fills"]["closeAvgPrice"] == 100000.0
    assert result["fills"]["openPriceSource"] == "userTrades"
    assert result["fills"]["closePriceSource"] == "userTrades"
    assert result["latency"]["openFillLookupMs"] == 24.0
    assert result["latency"]["closeFillLookupMs"] == 24.0
