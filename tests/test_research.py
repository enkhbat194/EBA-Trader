from __future__ import annotations

import eba_trader.research as research
from eba_trader.history import Candle


def make_candles(count: int = 160, step: int = 900_000) -> list[Candle]:
    rows: list[Candle] = []
    price = 100.0
    for index in range(count):
        if index < count // 2:
            price += 0.4
        else:
            price -= 0.15
        rows.append(
            Candle(
                open_time_ms=index * step,
                open=price - 0.1,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=100.0,
                close_time_ms=index * step + step - 1,
                quote_volume=10_000.0,
                trade_count=100,
            )
        )
    return rows


def test_baseline_study_uses_frozen_cost_scenarios(tmp_path, monkeypatch) -> None:
    candles = make_candles()
    monkeypatch.setattr(research, "fetch_binance_klines", lambda *args, **kwargs: candles)
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
