from __future__ import annotations

import math

from eba_trader.history import Candle
from eba_trader.orderflow_feature_dataset import OrderFlowFeatureRow
from eba_trader.strategy_discovery_v2 import DiscoveryCandidate, DiscoveryTrialStatus
from eba_trader.strategy_factory_v2_catalog import generate_pilot_candidates
from eba_trader.strategy_factory_v2_evaluator import (
    DiscoveryDatasetV2,
    SUPPORTED_FAMILIES,
    execute_discovery_candidate,
    make_d0_candidate_evaluator,
)


def _dataset(count: int = 260) -> DiscoveryDatasetV2:
    candles: list[Candle] = []
    rows: list[OrderFlowFeatureRow] = []
    cvd = 0.0
    start = 1_800_000_000_000
    for index in range(count):
        open_time = start + index * 60_000
        wave = ((index % 24) - 12) / 12.0
        drift = index * 0.025
        open_price = 100.0 + drift + wave
        direction = 1.0 if index % 7 in (0, 1, 2, 3) else -1.0
        close_price = open_price * (1.0 + direction * (0.001 + (index % 5) * 0.00025))
        high = max(open_price, close_price) * 1.0015
        low = min(open_price, close_price) * 0.9985
        volume = 100.0 + (index % 11) * 17.0
        candle = Candle(
            open_time_ms=open_time,
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume,
            close_time_ms=open_time + 59_999,
            quote_volume=volume * close_price,
            trade_count=100 + index % 20,
        )
        candles.append(candle)

        imbalance = 0.55 if index % 9 in (0, 1, 2, 3, 4) else -0.45
        executed = volume * (2.5 if index % 31 == 0 else 1.0)
        buy = executed * (1.0 + imbalance) / 2.0
        sell = executed - buy
        delta = buy - sell
        cvd += delta
        rows.append(
            OrderFlowFeatureRow(
                candle=candle,
                of_buy_volume=buy,
                of_sell_volume=sell,
                of_delta=delta,
                of_delta_ratio=delta / executed,
                of_cvd=cvd,
                of_poc_price=close_price,
                footprint_available_at_ms=open_time,
            )
        )
    return DiscoveryDatasetV2(candles=tuple(candles), orderflow_rows=tuple(rows))


def test_every_pilot_family_has_a_working_common_execution_adapter() -> None:
    dataset = _dataset()
    candidates = generate_pilot_candidates(seed="adapter-coverage")
    first_by_family: dict[str, DiscoveryCandidate] = {}
    for candidate in candidates:
        first_by_family.setdefault(candidate.family_id, candidate)

    assert set(first_by_family) == SUPPORTED_FAMILIES
    for family, candidate in first_by_family.items():
        execution = execute_discovery_candidate(dataset=dataset, candidate=candidate)
        assert execution.side in (-1, 1), family
        assert math.isfinite(execution.result.total_return), family
        assert math.isfinite(execution.result.expectancy), family
        assert 0.0 <= execution.result.exposure <= 1.0, family


def test_evaluator_emits_selection_only_metrics_and_behavior() -> None:
    dataset = _dataset()
    candidate = next(
        item
        for item in generate_pilot_candidates(seed="evaluator-metrics")
        if item.family_id == "donchian_breakout_v1"
    )
    evaluation = make_d0_candidate_evaluator(dataset)(candidate)

    assert evaluation.status in (DiscoveryTrialStatus.EVALUATED, DiscoveryTrialStatus.REJECTED)
    assert evaluation.metrics["selection_only"] is True
    assert evaluation.metrics["static_valid"] is True
    assert evaluation.behavior is not None
    assert len(evaluation.behavior.regime_returns) == 4
    assert 0.0 <= evaluation.behavior.exposure_fraction <= 1.0
    assert evaluation.behavior.turnover >= 0.0
    assert evaluation.compute_ms >= 0


def test_invalid_candidate_spec_fails_closed_without_performance_claim() -> None:
    dataset = _dataset()
    candidate = DiscoveryCandidate(
        family_id="donchian_breakout_v1",
        hypothesis_fingerprint="test-invalid",
        parameters={"entry_lookback": 4, "exit_lookback": 20},
    )
    evaluation = make_d0_candidate_evaluator(dataset)(candidate)

    assert evaluation.status is DiscoveryTrialStatus.REJECTED
    assert evaluation.metrics == {"selection_only": True, "static_valid": False}
    assert evaluation.behavior is None
    assert evaluation.rejection_reason == "invalid_candidate_spec:ValueError"


def test_orderflow_family_requires_aligned_orderflow_data() -> None:
    full = _dataset()
    price_only = DiscoveryDatasetV2(candles=full.candles)
    candidate = next(
        item
        for item in generate_pilot_candidates(seed="orderflow-required")
        if item.family_id == "volume_shock_momentum_v1"
    )
    evaluation = make_d0_candidate_evaluator(price_only)(candidate)

    assert evaluation.status is DiscoveryTrialStatus.REJECTED
    assert evaluation.metrics["static_valid"] is False
    assert evaluation.rejection_reason == "invalid_candidate_spec:ValueError"


def test_dataset_rejects_misaligned_price_and_orderflow_rows() -> None:
    full = _dataset()
    shifted = tuple(full.orderflow_rows[1:]) + (full.orderflow_rows[-1],)
    try:
        DiscoveryDatasetV2(candles=full.candles, orderflow_rows=shifted)
    except ValueError as exc:
        assert "time-aligned" in str(exc) or "identical lengths" in str(exc)
    else:
        raise AssertionError("misaligned D0 data must fail closed")
