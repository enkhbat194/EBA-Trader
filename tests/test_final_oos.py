from __future__ import annotations

import json

import pytest

import eba_trader.final_oos as final_oos
from eba_trader.history import Candle

STEP = 15 * 60 * 1000
COSTS = {
    "base": {"fee_bps": 10.0, "slippage_bps": 5.0},
    "adverse": {"fee_bps": 10.0, "slippage_bps": 10.0},
    "severe": {"fee_bps": 15.0, "slippage_bps": 20.0},
}


def make_window(start_ms: int, end_ms: int) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    count = (end_ms - start_ms) // STEP
    for index in range(count):
        phase = index % 80
        if phase < 25:
            price -= 0.15
        elif phase < 60:
            price += 0.35
        else:
            price -= 0.10
        ts = start_ms + index * STEP
        open_price = price - 0.05
        rows.append(
            Candle(
                open_time_ms=ts,
                open=open_price,
                high=max(open_price, price) + 0.30,
                low=min(open_price, price) - 0.30,
                close=price,
                volume=100.0,
                close_time_ms=ts + STEP - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def fake_frozen(tmp_path) -> dict[str, object]:
    return {
        "source_git_commit": "0123456789abcdef0123456789abcdef01234567",
        "symbol": "BTCUSDT",
        "interval": "15m",
        "initial_cash": 1000.0,
        "strategy": {"fast_ema": 5, "slow_ema": 15},
        "execution_policy": {
            "atr_period": 7,
            "atr_multiplier": 2.0,
            "risk_fraction": 0.005,
            "daily_loss_limit": 0.02,
            "max_drawdown_halt": 0.08,
        },
        "cost_scenarios": COSTS,
        "oos_window": {"start": "2025-01-01", "end_exclusive": "2025-01-03"},
        "oos_cache": str(tmp_path / "btcusdt_15m_out_of_sample.csv"),
    }


def test_final_oos_is_one_shot_and_writes_complete_marker(tmp_path, monkeypatch) -> None:
    frozen = fake_frozen(tmp_path)
    freeze_file = tmp_path / "freeze.json"
    freeze_file.write_text("{}", encoding="utf-8")
    marker = tmp_path / "opened.json"
    report_path = tmp_path / "oos.json"

    monkeypatch.setattr(final_oos, "_verify_final_freeze", lambda path: frozen)
    monkeypatch.setattr(
        final_oos,
        "fetch_binance_klines",
        lambda symbol, interval, start_ms, end_ms: make_window(start_ms, end_ms),
    )

    report = final_oos.run_final_oos(
        confirm_frozen=True,
        freeze_path=freeze_file,
        opened_marker_path=marker,
        report_path=report_path,
    )
    assert report["phase"] == "final_frozen_risk_execution_oos"
    assert report_path.exists()
    assert (tmp_path / "btcusdt_15m_out_of_sample.csv").exists()
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    assert marker_payload["status"] == "COMPLETE"
    assert marker_payload["rerun_policy"] == "forbidden"

    with pytest.raises(RuntimeError, match="already exists"):
        final_oos.run_final_oos(
            confirm_frozen=True,
            freeze_path=freeze_file,
            opened_marker_path=marker,
            report_path=report_path,
        )


def test_interrupted_open_marker_blocks_retry_before_network(tmp_path, monkeypatch) -> None:
    frozen = fake_frozen(tmp_path)
    freeze_file = tmp_path / "freeze.json"
    freeze_file.write_text("{}", encoding="utf-8")
    marker = tmp_path / "opened.json"
    marker.write_text('{"status":"OPENED_PENDING_RESULT"}', encoding="utf-8")

    monkeypatch.setattr(final_oos, "_verify_final_freeze", lambda path: frozen)

    def should_not_fetch(*args, **kwargs):
        pytest.fail("network must not be retried after OOS open marker exists")

    monkeypatch.setattr(final_oos, "fetch_binance_klines", should_not_fetch)
    with pytest.raises(RuntimeError, match="already opened"):
        final_oos.run_final_oos(
            confirm_frozen=True,
            freeze_path=freeze_file,
            opened_marker_path=marker,
            report_path=tmp_path / "oos.json",
        )


def test_final_oos_requires_explicit_confirmation(tmp_path) -> None:
    with pytest.raises(ValueError, match="confirm-frozen"):
        final_oos.run_final_oos(
            confirm_frozen=False,
            freeze_path=tmp_path / "freeze.json",
            opened_marker_path=tmp_path / "opened.json",
            report_path=tmp_path / "oos.json",
        )
