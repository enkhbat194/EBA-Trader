from eba_trader.derivatives_audit import DerivativeKline
from eba_trader.history import Candle
from eba_trader.m7_funding_flow import (
    FlowFeature,
    FundingEvent,
    FuturesFeatures,
    HorizonStats,
    YearStats,
    _passes_discovery,
    _spot_outcome,
    benjamini_hochberg,
    candidate_signal_indices,
    linear_percentile,
    prepare_futures_features,
)
from eba_trader.m7_funding_flow_policy import M7_CANDIDATES

BAR_MS = 15 * 60 * 1000


def _future_bar(index: int, *, gap_offset: int = 0) -> DerivativeKline:
    open_time = (index + gap_offset) * BAR_MS
    return DerivativeKline(
        open_time_ms=open_time,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        close_time_ms=open_time + BAR_MS - 1,
        volume=100.0,
        quote_volume=10_000.0,
        trade_count=100,
        taker_buy_base_volume=50.0,
        taker_buy_quote_volume=5_000.0,
    )


def _spot_bar(index: int, *, open_price: float = 100.0, close_price: float = 100.0) -> Candle:
    open_time = index * BAR_MS
    return Candle(
        open_time_ms=open_time,
        open=open_price,
        high=max(open_price, close_price) + 1.0,
        low=min(open_price, close_price) - 1.0,
        close=close_price,
        volume=100.0,
        close_time_ms=open_time + BAR_MS - 1,
        quote_volume=10_000.0,
        trade_count=100,
    )


def _candidate(name: str):
    return next(item for item in M7_CANDIDATES if item.name == name)


def test_linear_percentile_is_deterministic() -> None:
    assert linear_percentile([0.0, 10.0], 0.10) == 1.0
    assert linear_percentile([0.0, 10.0], 0.90) == 9.0


def test_flow_features_use_prior_activity_baseline_only() -> None:
    bars = [_future_bar(index) for index in range(100)]
    last = bars[-1]
    bars[-1] = DerivativeKline(
        open_time_ms=last.open_time_ms,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        close_time_ms=last.close_time_ms,
        volume=100.0,
        quote_volume=100_000.0,
        trade_count=400,
        taker_buy_base_volume=100.0,
        taker_buy_quote_volume=100_000.0,
    )
    features = prepare_futures_features(bars)
    feature = features.flow_1h[-1]
    assert feature is not None
    assert feature.quote_volume_intensity > 3.0
    assert feature.trade_count_intensity > 1.5
    assert feature.taker_buy_share > 0.60


def test_flow_features_reset_after_source_gap() -> None:
    bars = [_future_bar(index) for index in range(110)]
    for index in range(100, 110):
        bars[index] = _future_bar(index, gap_offset=1)
    features = prepare_futures_features(bars)
    assert features.flow_1h[-1] is None
    assert features.flow_4h[-1] is None


def test_funding_flow_waits_for_four_completed_bars() -> None:
    bars = tuple(_future_bar(index) for index in range(8))
    flow = [None] * len(bars)
    flow[3] = FlowFeature(
        taker_buy_share=0.60,
        quote_volume_intensity=1.0,
        trade_count_intensity=1.0,
        price_return=0.0,
    )
    features = FuturesFeatures(bars=bars, flow_1h=tuple(flow), flow_4h=tuple(flow))
    event = FundingEvent(
        funding_index=270,
        funding_time_ms=0,
        futures_bar_index=0,
        funding_rate=-0.001,
        q10=-0.0005,
        q90=0.0005,
        extreme_negative=True,
        extreme_positive=False,
    )
    indices = candidate_signal_indices(
        _candidate("funding_negative_post_buy"),
        features,
        (event,),
        signal_start_ms=0,
        signal_end_exclusive_ms=8 * BAR_MS,
    )
    assert indices == (3,)


def test_spot_outcome_enters_next_open_and_exits_frozen_horizon_close() -> None:
    bars = [_spot_bar(index) for index in range(20)]
    bars[11] = _spot_bar(11, open_price=100.0, close_price=100.0)
    bars[14] = _spot_bar(14, open_price=109.0, close_price=110.0)
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(bars)}
    outcome = _spot_outcome(
        bars,
        index_by_time,
        10 * BAR_MS,
        4,
        1,
        window_end_exclusive_ms=20 * BAR_MS,
    )
    assert outcome is not None
    assert round(outcome.gross_signed_return, 8) == 0.10
    assert round(outcome.base_net_signed_return, 8) == 0.097
    assert round(outcome.severe_net_signed_return, 8) == 0.093


def test_spot_outcome_refuses_gap_crossing() -> None:
    bars = [_spot_bar(index) for index in range(10)]
    bars.pop(3)
    index_by_time = {bar.open_time_ms: index for index, bar in enumerate(bars)}
    outcome = _spot_outcome(
        bars,
        index_by_time,
        2 * BAR_MS,
        4,
        1,
        window_end_exclusive_ms=10 * BAR_MS,
    )
    assert outcome is None


def test_benjamini_hochberg_is_monotone_and_bounded() -> None:
    adjusted = benjamini_hochberg({("a", 4): 0.001, ("b", 4): 0.02, ("c", 4): 0.20})
    assert 0.0 <= adjusted[("a", 4)] <= adjusted[("b", 4)] <= adjusted[("c", 4)] <= 1.0


def _passing_stats(*, uplift: float = 0.002, q_value: float = 0.05) -> HorizonStats:
    yearly = tuple(
        YearStats(
            year=year,
            event_count=20,
            mean_base_net=0.01,
            mean_severe_net=0.006,
            baseline_mean_base_net=0.008,
            baseline_uplift=0.002,
        )
        for year in (2021, 2022, 2023)
    )
    return HorizonStats(
        event_count=60,
        distinct_days=30,
        mean_gross_signed_return=0.015,
        mean_base_net_signed_return=0.012,
        mean_severe_net_signed_return=0.008,
        median_base_net_signed_return=0.010,
        base_net_win_rate=0.6,
        baseline_mean_base_net=0.012 - uplift,
        baseline_uplift=uplift,
        daily_mean_p_value=0.01,
        fdr_q_value=q_value,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
    )


def test_discovery_gate_requires_baseline_uplift_and_fdr() -> None:
    assert _passes_discovery(_passing_stats())
    assert not _passes_discovery(_passing_stats(uplift=0.0009))
    assert not _passes_discovery(_passing_stats(q_value=0.11))
