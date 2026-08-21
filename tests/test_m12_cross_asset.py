from dataclasses import replace

import pytest

from eba_trader.derivatives_audit import DerivativeKline
from eba_trader.history import Candle
from eba_trader.m12_cross_asset import (
    EventOutcome,
    HorizonStats,
    YearStats,
    _outcome_for_signal,
    _passes_challenge,
    _passes_discovery,
    accepted_signal_indices,
    benjamini_hochberg,
    candidate_matches,
    prepare_eth_features,
)
from eba_trader.m12_cross_asset_policy import M12_CANDIDATES

STEP = 15 * 60 * 1000


def _eth_bar(index: int, *, close: float | None = None, quote: float = 100.0) -> DerivativeKline:
    price = 100.0 + index * 0.1 if close is None else close
    volume = 10.0
    return DerivativeKline(
        open_time_ms=index * STEP,
        open=price,
        high=price * 1.001,
        low=price * 0.999,
        close=price,
        close_time_ms=(index + 1) * STEP - 1,
        volume=volume,
        quote_volume=quote,
        trade_count=100,
        taker_buy_base_volume=6.0,
        taker_buy_quote_volume=quote * 0.6,
    )


def _btc_bar(index: int, *, open_price: float | None = None, close: float | None = None) -> Candle:
    open_value = 100.0 if open_price is None else open_price
    close_value = open_value if close is None else close
    high = max(open_value, close_value) * 1.001
    low = min(open_value, close_value) * 0.999
    return Candle(
        open_time_ms=index * STEP,
        open=open_value,
        high=high,
        low=low,
        close=close_value,
        volume=10.0,
        close_time_ms=(index + 1) * STEP - 1,
        quote_volume=1000.0,
        trade_count=100,
    )


def _candidate(name: str):
    return next(item for item in M12_CANDIDATES if item.name == name)


def test_eth_features_use_completed_past_context_only() -> None:
    bars = [_eth_bar(index) for index in range(120)]
    bars[119] = _eth_bar(119, close=120.0, quote=400.0)
    features = prepare_eth_features(bars)
    assert features.ret_1h[119] == pytest.approx(120.0 / bars[115].close - 1.0)
    assert features.ret_4h[119] == pytest.approx(120.0 / bars[103].close - 1.0)
    assert features.taker_buy_share_1h[119] == pytest.approx(0.6)
    assert features.quote_volume_intensity_1h[119] is not None
    assert features.quote_volume_intensity_1h[119] > 1.0


def test_impulse_relative_and_flow_candidates_match_frozen_semantics() -> None:
    eth_bars = [_eth_bar(index) for index in range(120)]
    base = eth_bars[115].close
    eth_bars[119] = _eth_bar(119, close=base * 1.02, quote=400.0)
    eth = prepare_eth_features(eth_bars)
    btc = tuple(_btc_bar(index, close=100.0) for index in range(120))

    assert candidate_matches(_candidate("eth_1h_up_1_5"), eth, 119, btc, 119)
    assert candidate_matches(_candidate("eth_relative_1h_outperform_1"), eth, 119, btc, 119)
    assert candidate_matches(_candidate("eth_flow_1h_up_buy_confirm"), eth, 119, btc, 119)
    assert not candidate_matches(_candidate("eth_1h_down_1_5"), eth, 119, btc, 119)


def test_event_cooldown_is_four_signal_bars() -> None:
    eth_bars = [_eth_bar(index) for index in range(30)]
    for index in range(4, 30):
        eth_bars[index] = _eth_bar(index, close=eth_bars[index - 4].close * 1.02)
    eth = prepare_eth_features(eth_bars)
    btc = tuple(_btc_bar(index) for index in range(30))
    accepted = accepted_signal_indices(
        _candidate("eth_1h_up_1_5"),
        eth,
        btc,
        signal_start_ms=0,
        signal_end_exclusive_ms=30 * STEP,
    )
    assert accepted
    assert all(right - left >= 4 for left, right in zip(accepted, accepted[1:], strict=False))


def test_outcome_uses_next_btc_open_and_subtracts_frozen_costs() -> None:
    btc = tuple(
        _btc_bar(
            index,
            open_price=100.0 if index != 1 else 101.0,
            close=104.0 if index == 4 else 100.0,
        )
        for index in range(8)
    )
    outcome = _outcome_for_signal(
        btc,
        signal_index=0,
        horizon_bars=4,
        direction=1,
        window_end_exclusive_ms=8 * STEP,
    )
    assert outcome is not None
    gross = 104.0 / 101.0 - 1.0
    assert outcome.gross_signed_return == pytest.approx(gross)
    assert outcome.base_net_signed_return == pytest.approx(gross - 0.003)
    assert outcome.severe_net_signed_return == pytest.approx(gross - 0.007)


def test_outcome_rejects_noncontiguous_btc_path() -> None:
    btc = tuple([_btc_bar(0), _btc_bar(1), _btc_bar(3), _btc_bar(4), _btc_bar(5)])
    assert (
        _outcome_for_signal(
            btc,
            signal_index=0,
            horizon_bars=4,
            direction=1,
            window_end_exclusive_ms=10 * STEP,
        )
        is None
    )


def test_benjamini_hochberg_is_monotone_and_bounded() -> None:
    q = benjamini_hochberg({("a", 4): 0.001, ("b", 4): 0.02, ("c", 4): 0.5})
    assert 0 <= q[("a", 4)] <= q[("b", 4)] <= q[("c", 4)] <= 1
    assert q[("a", 4)] == pytest.approx(0.003)


def _passing_stats() -> HorizonStats:
    yearly = tuple(
        YearStats(
            year=year,
            event_count=30,
            mean_base_net=0.004,
            mean_severe_net=0.002,
            baseline_mean_base_net=0.001,
            baseline_uplift=0.003,
        )
        for year in (2021, 2022, 2023)
    )
    return HorizonStats(
        event_count=90,
        distinct_days=60,
        mean_gross_signed_return=0.009,
        mean_base_net_signed_return=0.006,
        mean_severe_net_signed_return=0.002,
        median_base_net_signed_return=0.004,
        base_net_win_rate=0.6,
        baseline_mean_base_net=0.001,
        baseline_uplift=0.005,
        daily_mean_p_value=0.001,
        fdr_q_value=0.01,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
    )


def test_discovery_gates_require_all_frozen_conditions() -> None:
    stats = _passing_stats()
    assert _passes_discovery(stats)
    assert not _passes_discovery(replace(stats, median_base_net_signed_return=-0.001))
    assert not _passes_discovery(replace(stats, baseline_uplift=0.0009))
    assert not _passes_discovery(replace(stats, fdr_q_value=0.11))


def test_challenge_is_blocked_without_discovery_pass() -> None:
    stats = replace(_passing_stats(), yearly=(), event_count=30)
    assert not _passes_challenge(stats, discovery_pass=False)
    assert _passes_challenge(stats, discovery_pass=True)


def test_negative_direction_outcome_remains_diagnostic_signed_return() -> None:
    outcome = EventOutcome(
        signal_time_ms=0,
        horizon_bars=4,
        gross_signed_return=0.01,
        base_net_signed_return=0.007,
        severe_net_signed_return=0.003,
    )
    assert outcome.base_net_signed_return > 0
