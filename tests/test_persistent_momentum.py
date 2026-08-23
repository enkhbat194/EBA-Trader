from __future__ import annotations

from eba_trader.persistence import TradeLedger
from eba_trader.persistent_momentum import PersistentMomentumPaperEngine


def _long_signal() -> dict[str, object]:
    return {
        "decision": "LONG",
        "score": 7,
        "atrPct": 0.003,
        "longScore": 7,
        "shortScore": 1,
        "rsi14": 60.0,
        "adx14": 30.0,
    }


def test_fast_momentum_survives_restart_and_close(tmp_path) -> None:
    ledger = TradeLedger(tmp_path / "eba_trader.db")
    session_key = "test-session"
    opened_at_ms = 1_700_000_000_000

    first = PersistentMomentumPaperEngine(ledger=ledger)
    with first._lock:
        opened, reason = first._open_locked(
            session_key,
            _long_signal(),
            0.0005,
            99.9,
            100.0,
            opened_at_ms,
        )

    assert opened is True
    assert reason == "MOMENTUM_SIGNAL_OPENED"
    row = ledger.list_positions(status="OPEN")[0]
    assert row["strategy"] == "FAST_MOMENTUM"
    assert row["side"] == "LONG"
    assert row["metadata"]["sessionKey"] == session_key
    assert row["metadata"]["entrySignal"]["score"] == 7

    restarted = PersistentMomentumPaperEngine(ledger=ledger)
    recovered = restarted.state(session_key)
    assert recovered["openPosition"] is not None
    assert recovered["openPosition"]["position_id"] == row["position_id"]
    assert recovered["openPosition"]["entry_price"] == 100.0

    closed_at_ms = opened_at_ms + 60_000
    with restarted._lock:
        position = restarted._positions[session_key]
        restarted._close_locked(
            session_key,
            position,
            100.5,
            closed_at_ms,
            "TAKE_PROFIT",
        )

    closed = ledger.get_position(row["position_id"])
    assert closed is not None
    assert closed["status"] == "CLOSED"
    assert closed["exit_price"] == 100.5
    assert closed["metadata"]["exitReason"] == "TAKE_PROFIT"

    second_restart = PersistentMomentumPaperEngine(ledger=ledger)
    final_state = second_restart.state(session_key)
    assert final_state["openPosition"] is None
    assert final_state["tradeCount"] == 1
    assert final_state["history"][0]["exit_reason"] == "TAKE_PROFIT"

    event_types = {event["event_type"] for event in ledger.list_events(limit=20)}
    assert "FAST_MOMENTUM_OPEN" in event_types
    assert "FAST_MOMENTUM_CLOSE" in event_types
