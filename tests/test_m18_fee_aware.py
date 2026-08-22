from __future__ import annotations

import hashlib
import hmac
import urllib.parse

import pytest

from eba_trader.m18_fee_aware import (
    BinanceReadOnlyClient,
    BookLevel,
    BookSnapshot,
    PairDecision,
    evaluate_cash_carry_snapshot,
    parse_futures_commission,
    parse_spot_commission,
    select_nearest_btcusdt_delivery_symbol,
    simulate_buy,
    simulate_sell,
)
from eba_trader.m18_fee_policy import M18ExecutionPolicy


def _spot_commission(*, taker: str = "0.001", discount: bool = False):
    return parse_spot_commission(
        {
            "symbol": "BTCUSDT",
            "standardCommission": {
                "maker": "0.001",
                "taker": taker,
                "buyer": "0.0001",
                "seller": "0.0002",
            },
            "specialCommission": {
                "maker": "0",
                "taker": "0.00001",
                "buyer": "0",
                "seller": "0",
            },
            "taxCommission": {
                "maker": "0",
                "taker": "0.00002",
                "buyer": "0",
                "seller": "0",
            },
            "discount": {
                "enabledForAccount": discount,
                "enabledForSymbol": discount,
                "discountAsset": "BNB",
                "discount": "0.75",
            },
        }
    )


def _futures_commission(*, taker: str = "0.0004"):
    return parse_futures_commission(
        {
            "symbol": "BTCUSDT_261225",
            "makerCommissionRate": "0.0002",
            "takerCommissionRate": taker,
            "rpiCommissionRate": "0.00005",
        }
    )


def _book(
    symbol: str,
    *,
    bids: tuple[tuple[float, float], ...],
    asks: tuple[tuple[float, float], ...],
    received_at_ms: int = 1_000,
) -> BookSnapshot:
    return BookSnapshot(
        symbol=symbol,
        bids=tuple(BookLevel(price=price, quantity=qty) for price, qty in bids),
        asks=tuple(BookLevel(price=price, quantity=qty) for price, qty in asks),
        received_at_ms=received_at_ms,
    )


def test_spot_commission_uses_role_side_special_tax_and_bnb_discount() -> None:
    plain = _spot_commission(discount=False)
    discounted = _spot_commission(discount=True)

    assert plain.effective_rate("BUY", "taker") == pytest.approx(0.00113)
    assert plain.effective_rate("SELL", "taker") == pytest.approx(0.00123)
    assert discounted.effective_rate("BUY", "taker") == pytest.approx(0.000855)
    assert discounted.effective_rate("SELL", "taker") == pytest.approx(0.00093)


def test_futures_commission_parser_reads_account_specific_rates() -> None:
    snapshot = _futures_commission()
    assert snapshot.symbol == "BTCUSDT_261225"
    assert snapshot.maker == pytest.approx(0.0002)
    assert snapshot.taker == pytest.approx(0.0004)
    assert snapshot.rpi == pytest.approx(0.00005)


def test_depth_vwap_consumes_multiple_levels() -> None:
    book = _book(
        "BTCUSDT",
        bids=((99.0, 1.0), (98.0, 2.0)),
        asks=((100.0, 1.0), (101.0, 2.0)),
    )
    buy = simulate_buy(book, 2.0)
    sell = simulate_sell(book, 2.0)
    assert buy is not None and sell is not None
    assert buy.vwap == pytest.approx(100.5)
    assert buy.worst_price == 101.0
    assert buy.levels_used == 2
    assert sell.vwap == pytest.approx(98.5)
    assert sell.worst_price == 98.0
    assert sell.levels_used == 2


def test_insufficient_depth_returns_no_fill() -> None:
    book = _book("BTCUSDT", bids=((99.0, 0.5),), asks=((100.0, 0.5),))
    assert simulate_buy(book, 1.0) is None
    assert simulate_sell(book, 1.0) is None


def test_fee_aware_gate_promotes_only_large_executable_premium_to_paper() -> None:
    spot_book = _book(
        "BTCUSDT",
        bids=((99.9, 10.0),),
        asks=((100.0, 10.0),),
    )
    futures_book = _book(
        "BTCUSDT_261225",
        bids=((103.0, 10.0),),
        asks=((103.1, 10.0),),
    )
    estimate = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=_spot_commission(taker="0.001", discount=False),
        futures_commission=_futures_commission(taker="0.0004"),
        quantity_btc=1.0,
        now_ms=1_100,
    )
    assert estimate.decision is PairDecision.PAPER_CANDIDATE
    assert estimate.gross_edge_bps is not None and estimate.gross_edge_bps > 100
    assert estimate.screening_net_edge_bps is not None
    assert estimate.screening_net_edge_bps >= 5.0
    assert estimate.live_execution_allowed is False


def test_costs_and_buffer_force_no_trade_when_premium_is_too_small() -> None:
    spot_book = _book(
        "BTCUSDT",
        bids=((99.99, 10.0),),
        asks=((100.0, 10.0),),
    )
    futures_book = _book(
        "BTCUSDT_261225",
        bids=((100.20, 10.0),),
        asks=((100.21, 10.0),),
    )
    estimate = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=_spot_commission(taker="0.001", discount=False),
        futures_commission=_futures_commission(taker="0.0004"),
        quantity_btc=1.0,
        now_ms=1_100,
    )
    assert estimate.decision is PairDecision.NO_TRADE
    assert "NET_EDGE_BELOW_MINIMUM" in estimate.reason_codes
    assert estimate.screening_net_edge_bps is not None


def test_stale_or_insufficient_books_are_deterministic_vetoes() -> None:
    spot_book = _book(
        "BTCUSDT",
        bids=((99.0, 10.0),),
        asks=((100.0, 10.0),),
        received_at_ms=1_000,
    )
    futures_book = _book(
        "BTCUSDT_261225",
        bids=((103.0, 0.1),),
        asks=((104.0, 10.0),),
        received_at_ms=1_000,
    )
    stale = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=_spot_commission(),
        futures_commission=_futures_commission(),
        quantity_btc=1.0,
        now_ms=3_000,
    )
    assert stale.decision is PairDecision.NO_TRADE
    assert "STALE_SPOT_BOOK" in stale.reason_codes
    assert "STALE_FUTURES_BOOK" in stale.reason_codes

    insufficient = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=_spot_commission(),
        futures_commission=_futures_commission(),
        quantity_btc=1.0,
        now_ms=1_100,
    )
    assert insufficient.decision is PairDecision.NO_TRADE
    assert insufficient.reason_codes == ("INSUFFICIENT_FUTURES_BID_DEPTH",)


def test_commission_symbol_mismatch_is_no_trade() -> None:
    spot_book = _book("BTCUSDT", bids=((99.0, 1.0),), asks=((100.0, 1.0),))
    futures_book = _book(
        "BTCUSDT_261225",
        bids=((103.0, 1.0),),
        asks=((104.0, 1.0),),
    )
    wrong_futures = parse_futures_commission(
        {
            "symbol": "BTCUSDT_270326",
            "makerCommissionRate": "0.0002",
            "takerCommissionRate": "0.0004",
        }
    )
    estimate = evaluate_cash_carry_snapshot(
        spot_book=spot_book,
        futures_book=futures_book,
        spot_commission=_spot_commission(),
        futures_commission=wrong_futures,
        quantity_btc=0.1,
        now_ms=1_100,
    )
    assert estimate.decision is PairDecision.NO_TRADE
    assert estimate.reason_codes == ("FUTURES_COMMISSION_SYMBOL_MISMATCH",)


def test_nearest_active_delivery_contract_is_selected_without_hardcoding() -> None:
    payload = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "deliveryDate": 9_999_999,
            },
            {
                "symbol": "BTCUSDT_260925",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "deliveryDate": 2_000,
            },
            {
                "symbol": "BTCUSDT_261225",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "deliveryDate": 3_000,
            },
            {
                "symbol": "BTCUSDT_260626",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "deliveryDate": 500,
            },
        ]
    }
    assert select_nearest_btcusdt_delivery_symbol(payload, now_ms=1_000) == "BTCUSDT_260925"


def test_signed_get_uses_hmac_and_client_exposes_no_order_method() -> None:
    class CapturingClient(BinanceReadOnlyClient):
        def __init__(self) -> None:
            super().__init__(api_key="key", api_secret="secret")
            self.captured_url = ""
            self.authenticated = False

        def _get_json(self, url: str, *, authenticated: bool):
            self.captured_url = url
            self.authenticated = authenticated
            return {"ok": True}

    client = CapturingClient()
    client._signed_get(
        "https://example.test",
        "/signed",
        {"symbol": "BTCUSDT", "recvWindow": 5000, "timestamp": 1234567890},
    )
    query = "symbol=BTCUSDT&recvWindow=5000&timestamp=1234567890"
    signature = hmac.new(b"secret", query.encode(), hashlib.sha256).hexdigest()
    expected = f"https://example.test/signed?{query}&signature={signature}"
    assert client.captured_url == expected
    assert client.authenticated is True
    assert not hasattr(client, "place_order")
    assert not hasattr(client, "cancel_order")
    assert urllib.parse.urlparse(client.captured_url).scheme == "https"


def test_policy_cannot_enable_live_execution_or_ai_authority() -> None:
    with pytest.raises(ValueError, match="live execution"):
        M18ExecutionPolicy(live_execution_allowed=True)
    with pytest.raises(ValueError, match="AI signal authority"):
        M18ExecutionPolicy(ai_signal_authority=True)
