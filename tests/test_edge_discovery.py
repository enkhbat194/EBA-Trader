from __future__ import annotations

from dataclasses import replace

import pytest

import eba_trader.edge_discovery as edge
from eba_trader.edge_discovery import (
    HorizonStats,
    YearStats,
    _outcome_for_event,
    _passes_challenge,
    _passes_discovery,
    _write_report_once,
    accepted_event_indices,
    benjamini_hochberg,
    prepare_edge_features,
)
from eba_trader.edge_discovery_policy import EDGE_CANDIDATES
from eba_trader.history import Candle


def _bar(
    index: int,
    *,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
    volume: float = 10.0,
) -> Candle:
    open_time = index * edge.FIFTEEN_MINUTES_MS
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time_ms=open_time + edge.FIFTEEN_MINUTES_MS - 1,
        quote_volume=volume * close,
        trade_count=1,
    )


def test_features_are_causal_and_prior_vwap_excludes_current_bar() -> None:
    bars = [_bar(index) for index in range(110)]
    bars[96] = _bar(
        96,
        open_price=1000.0,
        high=1001.0,
        low=999.0,
        close=1000.0,
        volume=1000.0,
    )

    features = prepare_edge_features(bars)

    assert features.prior_vwap[96] == pytest.approx(100.0)
    assert features.prior_median_volume[96] == pytest.approx(10.0)
    assert features.ret_1h[4] == pytest.approx(0.0)
    assert features.ret_4h[16] == pytest.approx(0.0)
    assert features.vwap_displacement_atr[96] > 0


def test_gap_resets_rolling_context_and_blocks_cross_gap_outcome() -> None:
    bars = [_bar(index) for index in range(50)] + [_bar(index) for index in range(51, 170)]

    features = prepare_edge_features(bars)

    assert features.contiguous_streak[50] == 1
    assert features.prior_vwap[50] is None
    assert _outcome_for_event(
        features,
        48,
        4,
        1,
        window_end_exclusive_ms=200 * edge.FIFTEEN_MINUTES_MS,
    ) is None


def test_forward_return_uses_next_open_and_frozen_round_trip_costs() -> None:
    bars = [_bar(index) for index in range(120)]
    bars[101] = _bar(101, open_price=100.0, high=101.0, low=99.0, close=100.0)
    bars[104] = _bar(104, open_price=101.0, high=103.0, low=100.0, close=102.0)
    features = prepare_edge_features(bars)

    outcome = _outcome_for_event(
        features,
        100,
        4,
        1,
        window_end_exclusive_ms=120 * edge.FIFTEEN_MINUTES_MS,
    )

    assert outcome is not None
    assert outcome.gross_signed_return == pytest.approx(0.02)
    assert outcome.base_net_signed_return == pytest.approx(0.017)
    assert outcome.severe_net_signed_return == pytest.approx(0.013)


def test_event_cooldown_suppresses_repeated_same_episode(monkeypatch) -> None:
    bars = tuple(_bar(index) for index in range(20))
    features = prepare_edge_features(bars)
    monkeypatch.setattr(edge, "candidate_matches", lambda candidate, supplied, index: True)

    accepted = accepted_event_indices(
        EDGE_CANDIDATES[0],
        features,
        signal_start_ms=0,
        signal_end_exclusive_ms=20 * edge.FIFTEEN_MINUTES_MS,
    )

    assert accepted == (0, 4, 8, 12, 16)


def test_benjamini_hochberg_adjustment_is_monotonic_and_bounded() -> None:
    p_values = {
        ("a", 4): 0.001,
        ("b", 4): 0.020,
        ("c", 4): 0.040,
    }

    adjusted = benjamini_hochberg(p_values)

    assert adjusted[("a", 4)] == pytest.approx(0.003)
    assert adjusted[("b", 4)] == pytest.approx(0.030)
    assert adjusted[("c", 4)] == pytest.approx(0.040)
    assert all(0.0 <= value <= 1.0 for value in adjusted.values())


def _qualifying_stats() -> HorizonStats:
    yearly = tuple(
        YearStats(year=year, event_count=20, mean_base_net=0.01, mean_severe_net=0.006)
        for year in edge.DISCOVERY_YEARS
    )
    return HorizonStats(
        event_count=60,
        distinct_days=30,
        mean_gross_signed_return=0.014,
        mean_base_net_signed_return=0.011,
        mean_severe_net_signed_return=0.007,
        median_base_net_signed_return=0.008,
        base_net_win_rate=0.60,
        daily_mean_p_value=0.01,
        fdr_q_value=0.05,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
    )


def test_discovery_and_challenge_gates_require_economic_and_temporal_stability() -> None:
    discovery = _qualifying_stats()
    assert _passes_discovery(discovery) is True

    broken_year = replace(
        discovery,
        yearly=discovery.yearly[:2]
        + (replace(discovery.yearly[2], mean_base_net=-0.001),),
    )
    assert _passes_discovery(broken_year) is False

    challenge = replace(
        discovery,
        event_count=20,
        yearly=(),
        fdr_q_value=1.0,
    )
    assert _passes_challenge(challenge, discovery_pass=True) is True
    assert _passes_challenge(challenge, discovery_pass=False) is False
    assert _passes_challenge(
        replace(challenge, median_base_net_signed_return=-0.001),
        discovery_pass=True,
    ) is False


def test_m5_report_writer_never_overwrites_first_result(tmp_path) -> None:
    report = tmp_path / "m5.json"
    _write_report_once(report, {"decision": "FIRST"})

    with pytest.raises(RuntimeError, match="already exists"):
        _write_report_once(report, {"decision": "SECOND"})

    assert '"FIRST"' in report.read_text(encoding="utf-8")
    assert "SECOND" not in report.read_text(encoding="utf-8")
