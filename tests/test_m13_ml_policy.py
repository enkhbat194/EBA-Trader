from pathlib import Path

from eba_trader.m13_ml_policy import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    HORIZONS_BARS,
    MODEL_FAMILIES,
    PROBABILITY_GATES,
    TEST_COUNT,
    canonical_text_sha256,
    verify_m13_freeze,
)


def test_m13_frozen_search_shape() -> None:
    assert FEATURE_COUNT == len(FEATURE_NAMES) == 19
    assert MODEL_FAMILIES == ("logistic", "hist_gb")
    assert PROBABILITY_GATES == (0.60, 0.65)
    assert HORIZONS_BARS == (4, 16, 48)
    assert len(MODEL_FAMILIES) * len(PROBABILITY_GATES) * len(HORIZONS_BARS) == TEST_COUNT == 12


def test_m13_freeze_manifest_verifies() -> None:
    manifest = verify_m13_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["parameter_changes_after_first_run"] == "forbidden"


def test_m13_protocol_hash_is_portable_across_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    assert canonical_text_sha256(lf) == canonical_text_sha256(crlf)
