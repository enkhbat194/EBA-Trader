import pytest

from eba_trader.mt5_bridge_store import MT5BridgeStore


def _snapshot() -> dict:
    return {
        "readOnly": True,
        "account": {"login": 123, "server": "MetaQuotes-Demo", "balance": 10000.0},
        "charts": {"XAUUSD": {"15m": []}},
        "positions": [],
    }


def test_pair_token_is_opaque_and_waiting_before_heartbeat() -> None:
    store = MT5BridgeStore(pair_ttl_seconds=60)
    pair = store.create_pair()
    token = pair["pairToken"]
    assert token
    assert pair["state"] == "waiting"
    state = store.state(token)
    assert state["connected"] is False
    assert state["state"] == "waiting"


def test_ingest_connects_bridge_and_returns_snapshot() -> None:
    store = MT5BridgeStore(pair_ttl_seconds=60)
    token = store.create_pair()["pairToken"]
    store.ingest(token, _snapshot())
    state = store.state(token)
    assert state["connected"] is True
    assert state["state"] == "connected"
    assert state["snapshot"]["account"]["login"] == 123
    assert state["liveExecutionAllowed"] is False


def test_revoke_and_unknown_tokens_fail_closed() -> None:
    store = MT5BridgeStore(pair_ttl_seconds=60)
    token = store.create_pair()["pairToken"]
    store.revoke(token)
    with pytest.raises(PermissionError, match="missing or expired"):
        store.state(token)
    with pytest.raises(PermissionError, match="missing or expired"):
        store.ingest("bad-token", _snapshot())
