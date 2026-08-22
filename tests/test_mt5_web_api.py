import pytest

from eba_trader.mt5_bridge_store import MT5BridgeStore
from eba_trader.web_server import (
    run_chart_request,
    run_mt5_disconnect_request,
    run_mt5_ingest_request,
    run_mt5_pair_request,
    run_mt5_state_request,
)


def _snapshot() -> dict:
    return {
        "readOnly": True,
        "account": {
            "login": 777,
            "server": "MetaQuotes-Demo",
            "currency": "USD",
            "balance": 10000.0,
            "equity": 10010.0,
        },
        "charts": {
            "XAUUSD": {
                "15m": [
                    {
                        "time": 1_700_000_000,
                        "open": 2000,
                        "high": 2005,
                        "low": 1998,
                        "close": 2003,
                        "volume": 10,
                    },
                    {
                        "time": 1_700_000_900,
                        "open": 2003,
                        "high": 2006,
                        "low": 2001,
                        "close": 2004,
                        "volume": 11,
                    },
                ]
            }
        },
        "positions": [],
        "markers": [],
    }


def test_mt5_pair_ingest_state_chart_disconnect_round_trip() -> None:
    store = MT5BridgeStore(pair_ttl_seconds=60)
    pair = run_mt5_pair_request(bridge_store=store)
    token = pair["pairToken"]
    assert pair["liveExecutionAllowed"] is False

    result = run_mt5_ingest_request(
        {"pairToken": token, "snapshot": _snapshot()},
        bridge_store=store,
    )
    assert result["state"] == "connected"

    state = run_mt5_state_request({"pairToken": token}, bridge_store=store)
    assert state["connected"] is True
    assert state["snapshot"]["account"]["login"] == 777

    chart = run_chart_request(
        {
            "provider": "metatrader5",
            "symbol": "XAUUSD",
            "timeframe": "15m",
            "pairToken": token,
        },
        bridge_store=store,
    )
    assert chart["provider"] == "metatrader5"
    assert chart["candles"][-1]["close"] == 2004.0
    assert chart["liveExecutionAllowed"] is False

    disconnected = run_mt5_disconnect_request({"pairToken": token}, bridge_store=store)
    assert disconnected["state"] == "disconnected"
    with pytest.raises(PermissionError):
        run_mt5_state_request({"pairToken": token}, bridge_store=store)


def test_mt5_ingest_rejects_non_read_only_bridge() -> None:
    store = MT5BridgeStore(pair_ttl_seconds=60)
    token = store.create_pair()["pairToken"]
    snapshot = _snapshot()
    snapshot["readOnly"] = False
    with pytest.raises(ValueError, match="readOnly=true"):
        run_mt5_ingest_request({"pairToken": token, "snapshot": snapshot}, bridge_store=store)
