from __future__ import annotations

import pytest

from eba_trader.orderflow_divergence import price_delta_divergence


def _score(
    *,
    high: float,
    low: float,
    delta: float,
    volume: float = 10.0,
    ref_highs=(100.0, 101.0, 102.0),
    ref_lows=(98.0, 99.0, 100.0),
    ref_deltas=(-0.6, -0.2, 0.1),
    ref_volumes=(10.0, 10.0, 10.0),
    minimum: float = 0.0,
):
    return price_delta_divergence(
        current_high=high,
        current_low=low,
        current_delta_ratio=delta,
        current_total_volume=volume,
        reference_highs=ref_highs,
        reference_lows=ref_lows,
        reference_delta_ratios=ref_deltas,
        reference_total_volumes=ref_volumes,
        min_total_volume=minimum,
    )


def test_new_low_with_weaker_selling_pressure_is_bullish_divergence() -> None:
    result = _score(high=101.0, low=97.0, delta=-0.2)

    assert result.bullish == pytest.approx(0.2)
    assert result.bearish == 0.0
    assert result.signed_score == pytest.approx(0.2)


def test_new_high_with_weaker_buying_pressure_is_bearish_divergence() -> None:
    result = _score(
        high=103.0,
        low=99.0,
        delta=0.2,
        ref_deltas=(-0.2, 0.1, 0.8),
    )

    assert result.bullish == 0.0
    assert result.bearish == pytest.approx(0.3)
    assert result.signed_score == pytest.approx(-0.3)


def test_equal_price_boundary_or_confirming_delta_is_neutral() -> None:
    assert _score(high=101.0, low=98.0, delta=-0.2).signed_score == 0.0
    assert _score(high=101.0, low=97.0, delta=-0.8).signed_score == 0.0


def test_zero_or_below_minimum_activity_fails_closed_to_neutral() -> None:
    assert _score(high=101.0, low=97.0, delta=-0.2, volume=0.0).signed_score == 0.0
    assert (
        _score(
            high=101.0,
            low=97.0,
            delta=-0.2,
            volume=5.0,
            ref_volumes=(5.0, 5.0, 5.0),
            minimum=5.0,
        ).signed_score
        == 0.0
    )


def test_outside_bar_with_both_divergences_is_ambiguous_and_neutral() -> None:
    result = _score(
        high=103.0,
        low=97.0,
        delta=0.0,
        ref_deltas=(-0.6, 0.1, 0.6),
    )

    assert result.bullish == 0.0
    assert result.bearish == 0.0
    assert result.signed_score == 0.0


def test_reference_order_does_not_change_score() -> None:
    first = _score(high=101.0, low=97.0, delta=-0.2)
    second = _score(
        high=101.0,
        low=97.0,
        delta=-0.2,
        ref_highs=(102.0, 101.0, 100.0),
        ref_lows=(100.0, 99.0, 98.0),
        ref_deltas=(0.1, -0.2, -0.6),
        ref_volumes=(10.0, 10.0, 10.0),
    )

    assert first == second


def test_tied_reference_extreme_uses_deterministic_strongest_confirmation() -> None:
    bullish = _score(
        high=101.0,
        low=97.0,
        delta=-0.3,
        ref_lows=(98.0, 98.0, 100.0),
        ref_deltas=(-0.7, -0.5, 0.1),
    )
    bearish = _score(
        high=103.0,
        low=99.0,
        delta=0.3,
        ref_highs=(102.0, 102.0, 100.0),
        ref_deltas=(0.8, 0.6, -0.1),
    )

    assert bullish.signed_score == pytest.approx(0.2)
    assert bearish.signed_score == pytest.approx(-0.25)


def test_insufficient_history_is_neutral_and_invalid_inputs_fail_closed() -> None:
    empty = price_delta_divergence(
        current_high=101.0,
        current_low=99.0,
        current_delta_ratio=0.0,
        current_total_volume=1.0,
        reference_highs=(),
        reference_lows=(),
        reference_delta_ratios=(),
        reference_total_volumes=(),
    )
    assert empty.signed_score == 0.0

    with pytest.raises(ValueError, match="equal lengths"):
        price_delta_divergence(
            current_high=101.0,
            current_low=99.0,
            current_delta_ratio=0.0,
            current_total_volume=1.0,
            reference_highs=(100.0,),
            reference_lows=(),
            reference_delta_ratios=(0.0,),
            reference_total_volumes=(1.0,),
        )
    with pytest.raises(ValueError, match="between -1 and 1"):
        _score(high=101.0, low=97.0, delta=1.1)
    with pytest.raises(ValueError, match="price range"):
        _score(high=96.0, low=97.0, delta=0.0)
