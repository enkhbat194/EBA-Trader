from __future__ import annotations

from eba_trader.m18_demo_snapshot import BinanceDemoReadOnlyClient, run_demo_fee_snapshot
from eba_trader.m18_fee_aware import (
    BookLevel,
    BookSnapshot,
    parse_futures_commission,
    parse_spot_commission,
)
from eba_trader.providers import CredentialEnvelope


def _credentials() -> CredentialEnvelope:
    return CredentialEnvelope(api_key="demo-key", api_secret="demo-secret")


def test_demo_client_exposes_no_live_execution_methods() -> None:
    client = BinanceDemoReadOnlyClient(_credentials())
    assert not hasattr(client, "place_order")
    assert not hasattr(client, "cancel_order")
    assert not hasattr(client, "withdraw")
    assert not hasattr(client, "change_leverage")


def test_demo_snapshot_fails_closed_when_demo_has_no_delivery_contract() -> None:
    class Client:
        def futures_exchange_info(self):
            return {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "baseAsset": "BTC",
                        "quoteAsset": "USDT",
                        "status": "TRADING",
                        "deliveryDate": 9_999_999_999_999,
                    }
                ]
            }

    result = run_demo_fee_snapshot(_credentials(), client=Client())
    assert result["decision"] == "NO_TRADE"
    assert result["reasonCodes"] == ["NO_ACTIVE_DEMO_DELIVERY_CONTRACT"]
    assert result["environment"] == "demo"
    assert result["liveExecutionAllowed"] is False


def test_demo_snapshot_can_return_fee_aware_paper_candidate(monkeypatch) -> None:
    now_ms = 2_000_000_000_000

    class Client:
        def futures_exchange_info(self):
            return {
                "symbols": [
                    {
                        "symbol": "BTCUSDT_401231",
                        "baseAsset": "BTC",
                        "quoteAsset": "USDT",
                        "status": "TRADING",
                        "deliveryDate": now_ms + 86_400_000,
                    }
                ]
            }

        def spot_commission(self):
            return parse_spot_commission(
                {
                    "symbol": "BTCUSDT",
                    "standardCommission": {
                        "maker": "0.0001",
                        "taker": "0.0001",
                        "buyer": "0",
                        "seller": "0",
                    },
                    "specialCommission": {},
                    "taxCommission": {},
                    "discount": {
                        "enabledForAccount": False,
                        "enabledForSymbol": False,
                        "discount": "1",
                    },
                }
            )

        def futures_commission(self, symbol):
            return parse_futures_commission(
                {
                    "symbol": symbol,
                    "makerCommissionRate": "0.0001",
                    "takerCommissionRate": "0.0001",
                }
            )

        def spot_book(self, *, limit):
            assert limit == 100
            return BookSnapshot(
                symbol="BTCUSDT",
                bids=(BookLevel(price=99.9, quantity=10),),
                asks=(BookLevel(price=100.0, quantity=10),),
                received_at_ms=now_ms,
            )

        def futures_book(self, symbol, *, limit):
            assert limit == 100
            return BookSnapshot(
                symbol=symbol,
                bids=(BookLevel(price=103.0, quantity=10),),
                asks=(BookLevel(price=103.1, quantity=10),),
                received_at_ms=now_ms,
            )

    monkeypatch.setattr("eba_trader.m18_demo_snapshot.time.time", lambda: now_ms / 1000)
    result = run_demo_fee_snapshot(_credentials(), quantity_btc=1.0, client=Client())
    assert result["decision"] == "PAPER_CANDIDATE"
    assert result["futuresSymbol"] == "BTCUSDT_401231"
    assert result["estimate"]["screening_net_edge_bps"] > 5.0
    assert result["liveExecutionAllowed"] is False
