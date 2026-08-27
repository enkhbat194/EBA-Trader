import math

import pytest

from eba_trader.orderflow import PriceLevelFlow, diagonal_imbalance_stacks


def _level(price: float, *, buy: float, sell: float) -> PriceLevelFlow:
    return PriceLevelFlow(price=price, buy_volume=buy, sell_volume=sell)


def test_buy_diagonal_stack_uses_exact_lower_bucket() -> None:
    levels = (
        _level(100.0, buy=1.0, sell=10.0),
        _level(101.0, buy=40.0, sell=10.0),
        _level(102.0, buy=45.0, sell=10.0),
        _level(103.0, buy=50.0, sell=10.0),
    )

    result = diagonal_imbalance_stacks(levels, price_step=1.0, ratio_threshold=3.0)

    assert result.buy_levels == 3
    assert result.sell_levels == 0
    assert result.signed_score == 3


def test_sell_diagonal_stack_uses_exact_upper_bucket() -> None:
    levels = (
        _level(100.0, buy=10.0, sell=40.0),
        _level(101.0, buy=10.0, sell=45.0),
        _level(102.0, buy=10.0, sell=50.0),
        _level(103.0, buy=10.0, sell=1.0),
    )

    result = diagonal_imbalance_stacks(levels, price_step=1.0, ratio_threshold=3.0)

    assert result.buy_levels == 0
    assert result.sell_levels == 3
    assert result.signed_score == -3


def test_missing_price_bucket_breaks_stack_instead_of_becoming_adjacent() -> None:
    levels = (
        _level(100.0, buy=1.0, sell=10.0),
        _level(102.0, buy=100.0, sell=1.0),
    )

    result = diagonal_imbalance_stacks(levels, price_step=1.0, ratio_threshold=3.0)

    assert result.buy_levels == 0
    assert result.sell_levels == 0
    assert result.signed_score == 0


def test_empty_diagonal_cell_does_not_create_infinite_imbalance() -> None:
    levels = (
        _level(100.0, buy=1.0, sell=0.0),
        _level(101.0, buy=100.0, sell=1.0),
    )

    result = diagonal_imbalance_stacks(levels, price_step=1.0, ratio_threshold=3.0)

    assert result.buy_levels == 0


def test_min_volume_is_strict_and_breaks_low_volume_cells() -> None:
    levels = (
        _level(100.0, buy=1.0, sell=1.0),
        _level(101.0, buy=10.0, sell=1.0),
    )

    result = diagonal_imbalance_stacks(
        levels,
        price_step=1.0,
        ratio_threshold=3.0,
        min_volume=1.0,
    )

    assert result.buy_levels == 0


def test_reversed_input_order_is_deterministic() -> None:
    levels = [
        _level(100.0, buy=1.0, sell=10.0),
        _level(101.0, buy=40.0, sell=10.0),
        _level(102.0, buy=45.0, sell=10.0),
    ]

    first = diagonal_imbalance_stacks(levels, price_step=1.0)
    second = diagonal_imbalance_stacks(list(reversed(levels)), price_step=1.0)

    assert first == second
    assert first.buy_levels == 2


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"price_step": 0.0}, "price_step"),
        ({"price_step": math.inf}, "price_step"),
        ({"price_step": 1.0, "ratio_threshold": 1.0}, "ratio_threshold"),
        ({"price_step": 1.0, "min_volume": -1.0}, "min_volume"),
    ],
)
def test_invalid_stacked_configuration_fails_closed(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        diagonal_imbalance_stacks([], **kwargs)


def test_duplicate_or_invalid_price_levels_fail_closed() -> None:
    duplicate = (
        _level(100.0, buy=1.0, sell=1.0),
        _level(100.0, buy=2.0, sell=2.0),
    )
    with pytest.raises(ValueError, match="unique"):
        diagonal_imbalance_stacks(duplicate, price_step=1.0)

    invalid = (_level(100.0, buy=-1.0, sell=1.0),)
    with pytest.raises(ValueError, match="non-negative"):
        diagonal_imbalance_stacks(invalid, price_step=1.0)
