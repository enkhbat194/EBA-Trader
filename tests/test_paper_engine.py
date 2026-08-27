from eba_trader.paper_engine import DELIVERY_EXIT_BUFFER_MS, PaperExecutionEngine


def _candidate(*, capital=1000.0, delivery=2_000_000_000_000):
    return {
        "decision": "PAPER_CANDIDATE",
        "futuresSymbol": "BTCUSDT_401231",
        "futuresDeliveryTimeMs": delivery,
        "estimate": {
            "spot_symbol": "BTCUSDT",
            "futures_symbol": "BTCUSDT_401231",
            "quantity_btc": 1.0,
            "spot_entry_vwap": 100.0,
            "futures_entry_vwap": 103.0,
            "entry_fee_usd": 0.20,
            "fully_funded_capital_usd": capital,
        },
        "closeQuote": {
            "spotExitVwap": 101.0,
            "futuresExitVwap": 102.0,
            "exitFeeUsd": 0.20,
        },
    }


def _legacy_engine(**kwargs) -> PaperExecutionEngine:
    return PaperExecutionEngine(allow_new_entries=True, **kwargs)


def test_default_engine_retires_new_carry_entries() -> None:
    engine = PaperExecutionEngine()
    state = engine.step("s", _candidate(), now_ms=1000)
    assert state["openPosition"] is None
    assert state["history"] == []
    assert state["event"] == "NO_ACTION"
    assert state["reason"] == "LEGACY_CARRY_RETIRED"
    assert state["legacyCarryRetired"] is True
    assert state["newEntriesAllowed"] is False
    assert state["liveExecutionAllowed"] is False


def test_no_trade_does_not_open_paper_position() -> None:
    engine = _legacy_engine()
    state = engine.step("s", {"decision": "NO_TRADE"}, now_ms=1000)
    assert state["openPosition"] is None
    assert state["history"] == []
    assert state["event"] == "NO_ACTION"


def test_candidate_opens_only_one_paired_paper_position() -> None:
    engine = _legacy_engine()
    first = engine.step("s", _candidate(), now_ms=1000)
    assert first["event"] == "PAPER_ENTRY"
    assert first["openPosition"]["spot_entry_vwap"] == 100.0
    assert first["openPosition"]["futures_entry_vwap"] == 103.0
    second = engine.step("s", _candidate(), now_ms=2000)
    assert second["event"] == "PAPER_MARK"
    assert second["openPosition"]["position_id"] == first["openPosition"]["position_id"]


def test_paper_mark_uses_executable_pair_close_and_both_fees() -> None:
    engine = _legacy_engine()
    engine.step("s", _candidate(), now_ms=1000)
    marked = engine.step("s", _candidate(), now_ms=2000)
    # Spot +1 plus short future +1 = +2 gross; 0.20 entry + 0.20 exit fees.
    assert marked["openPosition"]["unrealized_gross_usd"] == 2.0
    assert marked["unrealizedPnlUsd"] == 1.6
    assert marked["liveExecutionAllowed"] is False


def test_manual_paper_close_creates_history_and_entry_exit_markers() -> None:
    engine = _legacy_engine()
    engine.step("s", _candidate(), now_ms=1000)
    closed = engine.close("s", _candidate(), now_ms=3000)
    assert closed["openPosition"] is None
    assert len(closed["history"]) == 1
    assert closed["history"][0]["net_pnl_usd"] == 1.6
    assert [marker["kind"] for marker in closed["markers"]] == ["BUY", "EXIT"]


def test_paper_capital_limit_fails_closed() -> None:
    engine = _legacy_engine(max_capital_usd=10_000)
    state = engine.step("s", _candidate(capital=10_001), now_ms=1000)
    assert state["openPosition"] is None
    assert state["reason"] == "PAPER_CAPITAL_LIMIT"


def test_entry_can_be_disabled_while_existing_position_still_marks() -> None:
    engine = _legacy_engine()
    no_entry = engine.step("s", _candidate(), allow_entry=False, now_ms=1000)
    assert no_entry["openPosition"] is None
    assert no_entry["reason"] == "ENTRY_SCANNER_STOPPED"
    engine.step("s", _candidate(), allow_entry=True, now_ms=2000)
    marked = engine.step("s", _candidate(), allow_entry=False, now_ms=3000)
    assert marked["event"] == "PAPER_MARK"
    assert marked["openPosition"] is not None


def test_delivery_safety_exit_closes_15_minutes_before_delivery() -> None:
    delivery = 2_000_000_000
    engine = _legacy_engine()
    engine.step("s", _candidate(delivery=delivery), now_ms=1000)
    state = engine.step(
        "s",
        _candidate(delivery=delivery),
        now_ms=delivery - DELIVERY_EXIT_BUFFER_MS,
    )
    assert state["event"] == "PAPER_EXIT"
    assert state["openPosition"] is None
    assert state["history"][0]["exit_reason"] == "DELIVERY_SAFETY_EXIT"
