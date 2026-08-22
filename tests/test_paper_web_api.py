from eba_trader.demo_sessions import DemoSessionStore
from eba_trader.paper_engine import PaperExecutionEngine
from eba_trader.providers import CredentialEnvelope
from eba_trader.web_server import (
    run_demo_disconnect_request,
    run_paper_close_request,
    run_paper_state_request,
    run_paper_step_request,
)


def _candidate() -> dict:
    return {
        "decision": "PAPER_CANDIDATE",
        "futuresSymbol": "BTCUSDT_401231",
        "futuresDeliveryTimeMs": 9_999_999_999_999,
        "estimate": {
            "spot_symbol": "BTCUSDT",
            "futures_symbol": "BTCUSDT_401231",
            "quantity_btc": 0.001,
            "spot_entry_vwap": 100_000.0,
            "futures_entry_vwap": 101_000.0,
            "entry_fee_usd": 0.05,
            "fully_funded_capital_usd": 201.0,
        },
        "closeQuote": {
            "spotExitVwap": 100_100.0,
            "futuresExitVwap": 100_800.0,
            "exitFeeUsd": 0.05,
        },
        "liveExecutionAllowed": False,
    }


def test_paper_step_state_close_and_disconnect_are_session_scoped(monkeypatch) -> None:
    store = DemoSessionStore(ttl_seconds=60)
    engine = PaperExecutionEngine()
    token = store.create(CredentialEnvelope(api_key="demo", api_secret="secret"))
    monkeypatch.setattr("eba_trader.web_server.run_demo_fee_snapshot", lambda credentials: _candidate())

    stepped = run_paper_step_request(
        {"sessionToken": token},
        session_store=store,
        paper_engine=engine,
    )
    assert stepped["paper"]["event"] == "PAPER_ENTRY"
    assert stepped["liveExecutionAllowed"] is False

    state = run_paper_state_request(
        {"sessionToken": token},
        session_store=store,
        paper_engine=engine,
    )
    assert state["openPosition"] is not None

    closed = run_paper_close_request(
        {"sessionToken": token},
        session_store=store,
        paper_engine=engine,
    )
    assert closed["paper"]["event"] == "PAPER_EXIT"
    assert len(closed["paper"]["history"]) == 1

    run_demo_disconnect_request(
        {"sessionToken": token},
        session_store=store,
        paper_engine=engine,
    )
    assert store.get(token) is None
    assert engine.state(token)["history"] == []
