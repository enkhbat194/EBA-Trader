from pathlib import Path

from eba_trader.persistence import PositionRecord, TradeLedger


def test_position_survives_ledger_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "ledger.db"

    first = TradeLedger(db_path)
    first.upsert_position(
        PositionRecord(
            position_id="paper-1",
            symbol="BTCUSDT",
            side="LONG",
            status="OPEN",
            entry_price=77000.0,
            quantity=0.001,
            leverage=5.0,
            take_profit=77500.0,
            stop_loss=76750.0,
            opened_at="2026-08-24T00:00:00Z",
            strategy="fast_momentum",
            metadata={"paper": True},
        )
    )
    first.append_event("POSITION_OPENED", position_id="paper-1", payload={"paper": True})

    reopened = TradeLedger(db_path)
    position = reopened.get_position("paper-1")
    assert position is not None
    assert position["status"] == "OPEN"
    assert position["metadata"] == {"paper": True}
    assert reopened.list_events()[0]["event_type"] == "POSITION_OPENED"


def test_position_can_be_closed_without_losing_history(tmp_path: Path) -> None:
    ledger = TradeLedger(tmp_path / "ledger.db")
    ledger.upsert_position(
        PositionRecord(
            position_id="paper-2",
            symbol="BTCUSDT",
            side="SHORT",
            status="OPEN",
            entry_price=77000.0,
            quantity=0.001,
        )
    )
    ledger.upsert_position(
        PositionRecord(
            position_id="paper-2",
            symbol="BTCUSDT",
            side="SHORT",
            status="CLOSED",
            entry_price=77000.0,
            quantity=0.001,
            closed_at="2026-08-24T00:05:00Z",
            exit_price=76800.0,
            realized_pnl=0.20,
        )
    )

    assert ledger.list_positions(status="OPEN") == []
    closed = ledger.list_positions(status="CLOSED")
    assert len(closed) == 1
    assert closed[0]["exit_price"] == 76800.0
    assert closed[0]["realized_pnl"] == 0.20
