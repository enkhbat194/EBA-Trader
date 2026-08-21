from eba_trader.m14_carry_policy import (
    CONFIG_COUNT,
    FUNDING_THRESHOLDS,
    HOLD_RECORDS,
    verify_m14_freeze,
)


def test_m14_frozen_config_shape() -> None:
    assert FUNDING_THRESHOLDS == (0.0001, 0.0003, 0.0005)
    assert HOLD_RECORDS == (3, 9)
    assert len(FUNDING_THRESHOLDS) * len(HOLD_RECORDS) == CONFIG_COUNT == 6


def test_m14_freeze_manifest_verifies() -> None:
    manifest = verify_m14_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["leverage"] == "forbidden"
    assert manifest["naked_short"] == "forbidden"
