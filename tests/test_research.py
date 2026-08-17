from __future__ import annotations

import json

import pytest

import eba_trader.research as research
from eba_trader.freeze import freeze_oos_candidate
from eba_trader.history import Candle, INTERVAL_MS

STEP = INTERVAL_MS["15m"]


def make_window(start_ms: int, end_ms: int, step: int = STEP) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    count = (end_ms - start_ms) // step
    for index in range(count):
        phase = index % 240
        if phase < 80:
            price -= 0.12
        elif phase < 180:
            price += 0.28
        else:
            price -= 0.08
        ts = start_ms + index * step
        rows.append(
            Candle(
                open_time_ms=ts,
                open=price - 0.1,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=100.0,
                close_time_ms=ts + step - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def exact_fake_fetch(symbol: str, interval: str, start_ms: int, end_ms: int, **kwargs):
    assert symbol == "BTCUSDT"
    assert interval == "15m"
    return make_window(start_ms, end_ms)


def make_frozen_candidate(tmp_path, *, fast: int = 5, slow: int = 15):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    development = tmp_path / "development.json"
    development.write_text(
        json.dumps(
            {
                "phase": "development_only",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_dir": str(data_dir),
                "oos_2025": "LOCKED_NOT_ACCESSED",
                "frozen_baseline": {"fast_ema": fast, "slow_ema": slow},
            }
        ),
        encoding="utf-8",
    )
    frozen = tmp_path / "freeze.json"
    freeze_oos_candidate(
        development_report_path=development,
        freeze_path=frozen,
    )
    return development, frozen


def test_default_baseline_windows_keep_2025_oos_locked() -> None:
    assert [window.name for window in research.DEFAULT_WINDOWS] == ["research", "validation"]
    assert research.OOS_WINDOW.name == "out_of_sample"
    assert research.OOS_WINDOW.start == "2025-01-01"


def test_baseline_study_uses_frozen_cost_scenarios(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(research, "fetch_binance_klines", exact_fake_fetch)
    windows = (research.StudyWindow("research", "2021-01-01", "2021-01-03"),)

    report = research.run_baseline_study(
        data_dir=tmp_path / "data",
        report_path=tmp_path / "report.json",
        windows=windows,
        fast_ema=5,
        slow_ema=15,
    )

    scenarios = report["windows"]["research"]["scenarios"]
    assert set(scenarios) == {"base", "adverse", "severe"}
    assert scenarios["severe"]["final_equity"] <= scenarios["base"]["final_equity"]
    assert (tmp_path / "report.json").exists()
    assert report["parameter_tuning"] is False
    assert report["holdout"]["status"] == "locked_not_downloaded"
    assert report["holdout"]["cache_verified_absent"] is True
    assert report["windows"]["research"]["coverage"] == "exact"
    assert "out_of_sample" not in report["windows"]


def test_baseline_refuses_direct_oos_window(tmp_path) -> None:
    with pytest.raises(ValueError, match="out-of-sample"):
        research.run_baseline_study(
            data_dir=tmp_path / "data",
            report_path=tmp_path / "report.json",
            windows=(research.OOS_WINDOW,),
            fast_ema=5,
            slow_ema=15,
        )


def test_development_refuses_preexisting_oos_cache(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    oos_cache = data_dir / "btcusdt_15m_out_of_sample.csv"
    oos_cache.write_text("contaminated", encoding="utf-8")

    with pytest.raises(RuntimeError, match="OOS cache already exists"):
        research.run_baseline_study(
            data_dir=data_dir,
            report_path=tmp_path / "report.json",
            windows=(),
            fast_ema=5,
            slow_ema=15,
        )


def test_frozen_oos_requires_explicit_confirmation(tmp_path) -> None:
    with pytest.raises(ValueError, match="locked"):
        research.run_frozen_oos_study(
            confirm_frozen=False,
            data_dir=tmp_path / "data",
            report_path=tmp_path / "oos.json",
            freeze_path=tmp_path / "freeze.json",
            development_report_path=tmp_path / "development.json",
        )


def test_frozen_oos_uses_frozen_parameters_and_blocks_rerun(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(research, "fetch_binance_klines", exact_fake_fetch)
    development, frozen = make_frozen_candidate(tmp_path, fast=5, slow=15)
    report_path = tmp_path / "oos.json"

    report = research.run_frozen_oos_study(
        confirm_frozen=True,
        data_dir=tmp_path / "data",
        report_path=report_path,
        freeze_path=frozen,
        development_report_path=development,
    )
    assert report["phase"] == "frozen_out_of_sample"
    assert report["fast_ema"] == 5
    assert report["slow_ema"] == 15
    assert report["retuning_after_open"] == "forbidden"
    assert report["window"]["coverage"] == "exact"
    assert report_path.exists()

    with pytest.raises(RuntimeError, match="already exists"):
        research.run_frozen_oos_study(
            confirm_frozen=True,
            data_dir=tmp_path / "data",
            report_path=report_path,
            freeze_path=frozen,
            development_report_path=development,
        )


def test_json_profit_factor_never_emits_infinity() -> None:
    result = type(
        "Result",
        (),
        {
            "initial_cash": 1000.0,
            "final_equity": 1100.0,
            "total_return": 0.1,
            "annualized_return": 0.1,
            "benchmark_return": 0.05,
            "benchmark_relative_return": 0.05,
            "max_drawdown": -0.1,
            "trade_count": 1,
            "win_rate": 1.0,
            "profit_factor": float("inf"),
            "expectancy": 100.0,
            "average_win": 100.0,
            "average_loss": 0.0,
            "sharpe": 1.0,
            "sortino": 2.0,
            "exposure": 0.5,
            "total_cost": 1.0,
        },
    )()
    assert research.result_to_dict(result)["profit_factor"] is None
