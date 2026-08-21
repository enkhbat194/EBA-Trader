from dataclasses import replace

import pytest

from eba_trader.history import Candle
from eba_trader.m13_ml_edge import (
    EvaluationStats,
    MLSample,
    YearStats,
    _outcome,
    _passes_challenge,
    _passes_discovery,
    benjamini_hochberg,
    selected_events,
    walk_forward_predictions,
)
from eba_trader.m13_ml_policy import FEATURE_COUNT

STEP = 15 * 60 * 1000


def _spot_bar(index: int, *, open_price: float = 100.0, close: float = 100.0) -> Candle:
    return Candle(
        open_time_ms=index * STEP,
        open=open_price,
        high=max(open_price, close) * 1.001,
        low=min(open_price, close) * 0.999,
        close=close,
        volume=10.0,
        close_time_ms=(index + 1) * STEP - 1,
        quote_volume=1000.0,
        trade_count=100,
    )


def _sample(index: int, year: int, signal: float, gross: float) -> MLSample:
    features = (signal,) + tuple(0.0 for _ in range(FEATURE_COUNT - 1))
    return MLSample(
        signal_time_ms=index * 60 * 60 * 1000,
        year=year,
        features=features,
        gross_returns={4: gross},
    )


def test_outcome_uses_next_open_and_horizon_close() -> None:
    bars = tuple(
        _spot_bar(
            index,
            open_price=101.0 if index == 1 else 100.0,
            close=104.0 if index == 4 else 100.0,
        )
        for index in range(8)
    )
    assert _outcome(bars, 0, 4) == pytest.approx(104.0 / 101.0 - 1.0)


def test_outcome_rejects_gap() -> None:
    bars = (
        _spot_bar(0),
        _spot_bar(1),
        _spot_bar(2),
        _spot_bar(4),
        _spot_bar(5),
    )
    assert _outcome(bars, 0, 4) is None


def test_walk_forward_predictions_are_strictly_out_of_sample_by_year() -> None:
    samples = []
    index = 0
    for year, count in ((2021, 120), (2022, 80), (2023, 80)):
        for offset in range(count):
            signal = -1.0 if offset % 2 == 0 else 1.0
            gross = -0.01 if signal < 0 else 0.01
            samples.append(_sample(index, year, signal, gross))
            index += 1
    predictions = walk_forward_predictions(tuple(samples), "logistic", 4)
    assert len(predictions) == 160
    assert {sample.year for sample, _ in predictions} == {2022, 2023}
    assert all(0.0 <= probability <= 1.0 for _, probability in predictions)


def test_selected_events_apply_frozen_probability_gate_and_costs() -> None:
    predictions = (
        (_sample(1, 2022, 1.0, 0.02), 0.70),
        (_sample(2, 2022, 1.0, 0.02), 0.59),
    )
    events = selected_events(predictions, horizon=4, probability_gate=0.60)
    assert len(events) == 1
    assert events[0].base_net_return == pytest.approx(0.017)
    assert events[0].severe_net_return == pytest.approx(0.013)


def test_benjamini_hochberg_is_monotone() -> None:
    adjusted = benjamini_hochberg({"a": 0.001, "b": 0.02, "c": 0.5})
    assert 0 <= adjusted["a"] <= adjusted["b"] <= adjusted["c"] <= 1
    assert adjusted["a"] == pytest.approx(0.003)


def _passing_discovery_stats() -> EvaluationStats:
    yearly = tuple(
        YearStats(
            year=year,
            event_count=50,
            mean_base_net=0.004,
            mean_severe_net=0.002,
        )
        for year in (2022, 2023)
    )
    return EvaluationStats(
        event_count=100,
        distinct_days=60,
        mean_gross=0.009,
        mean_base_net=0.006,
        mean_severe_net=0.002,
        median_base_net=0.004,
        profit_factor_base=1.5,
        win_rate_base=0.6,
        daily_mean_p_value=0.001,
        fdr_q_value=0.01,
        positive_months=12,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
        status="MEASURED",
    )


def test_discovery_gates_require_severe_median_pf_years_and_fdr() -> None:
    stats = _passing_discovery_stats()
    assert _passes_discovery(stats)
    assert not _passes_discovery(replace(stats, mean_severe_net=-0.001))
    assert not _passes_discovery(replace(stats, median_base_net=-0.001))
    assert not _passes_discovery(replace(stats, profit_factor_base=1.05))
    assert not _passes_discovery(replace(stats, fdr_q_value=0.11))


def test_challenge_gates_require_monthly_stability() -> None:
    stats = replace(
        _passing_discovery_stats(),
        event_count=60,
        positive_months=6,
        yearly=(YearStats(2024, 60, 0.004, 0.002),),
    )
    assert _passes_challenge(stats)
    assert not _passes_challenge(replace(stats, positive_months=5))
