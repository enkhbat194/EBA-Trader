from __future__ import annotations

from collections import Counter

from eba_trader.edge_discovery_policy import (
    BASE_ROUND_TRIP_COST_BPS,
    EDGE_CANDIDATES,
    EDGE_DISCOVERY_POLICY_NAME,
    EDGE_DISCOVERY_PROTOCOL_SHA256,
    EVENT_COOLDOWN_BARS,
    FDR_Q_THRESHOLD,
    HORIZONS_BARS,
    MIN_CHALLENGE_EVENTS,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_YEAR,
    SEVERE_ROUND_TRIP_COST_BPS,
    canonical_text_sha256,
    verify_edge_discovery_freeze,
)

EXPECTED_CANDIDATES = (
    ("ret_1h_up_1_5", "return_impulse", 1, 4, 0.015, None, None, None),
    ("ret_1h_up_2_5", "return_impulse", 1, 4, 0.025, None, None, None),
    ("ret_4h_up_3_0", "return_impulse", 1, 16, 0.030, None, None, None),
    ("ret_4h_up_5_0", "return_impulse", 1, 16, 0.050, None, None, None),
    ("ret_1h_down_1_5", "return_impulse", -1, 4, 0.015, None, None, None),
    ("ret_1h_down_2_5", "return_impulse", -1, 4, 0.025, None, None, None),
    ("ret_4h_down_3_0", "return_impulse", -1, 16, 0.030, None, None, None),
    ("ret_4h_down_5_0", "return_impulse", -1, 16, 0.050, None, None, None),
    ("volume_ret_1h_up_1_5_x1_5", "volume_impulse", 1, 4, 0.015, 1.5, None, None),
    ("volume_ret_1h_up_1_5_x2_0", "volume_impulse", 1, 4, 0.015, 2.0, None, None),
    ("volume_ret_4h_up_3_0_x1_5", "volume_impulse", 1, 16, 0.030, 1.5, None, None),
    ("volume_ret_4h_up_3_0_x2_0", "volume_impulse", 1, 16, 0.030, 2.0, None, None),
    ("volume_ret_1h_down_1_5_x1_5", "volume_impulse", -1, 4, 0.015, 1.5, None, None),
    ("volume_ret_1h_down_1_5_x2_0", "volume_impulse", -1, 4, 0.015, 2.0, None, None),
    ("volume_ret_4h_down_3_0_x1_5", "volume_impulse", -1, 16, 0.030, 1.5, None, None),
    ("volume_ret_4h_down_3_0_x2_0", "volume_impulse", -1, 16, 0.030, 2.0, None, None),
    ("vwap_up_1_0_atr", "vwap_displacement", 1, None, None, None, 1.0, None),
    ("vwap_up_2_0_atr", "vwap_displacement", 1, None, None, None, 2.0, None),
    ("vwap_down_1_0_atr", "vwap_displacement", -1, None, None, None, 1.0, None),
    ("vwap_down_2_0_atr", "vwap_displacement", -1, None, None, None, 2.0, None),
    ("compressed_breakout_up_vol_1_5", "compressed_breakout", 1, None, None, 1.5, None, 0.80),
    ("compressed_breakout_up_vol_2_0", "compressed_breakout", 1, None, None, 2.0, None, 0.80),
    ("compressed_breakout_down_vol_1_5", "compressed_breakout", -1, None, None, 1.5, None, 0.80),
    ("compressed_breakout_down_vol_2_0", "compressed_breakout", -1, None, None, 2.0, None, 0.80),
)


def test_m5_search_space_is_exactly_frozen_to_24_unique_candidates() -> None:
    assert len(EDGE_CANDIDATES) == 24
    assert len({item.name for item in EDGE_CANDIDATES}) == 24
    assert len(EDGE_CANDIDATES) * len(HORIZONS_BARS) == 72
    assert Counter(item.family for item in EDGE_CANDIDATES) == {
        "return_impulse": 8,
        "volume_impulse": 8,
        "vwap_displacement": 4,
        "compressed_breakout": 4,
    }
    assert sum(item.direction > 0 for item in EDGE_CANDIDATES) == 12
    assert sum(item.direction < 0 for item in EDGE_CANDIDATES) == 12
    assert tuple(
        (
            item.name,
            item.family,
            item.direction,
            item.return_lookback_bars,
            item.return_threshold,
            item.volume_ratio_min,
            item.displacement_atr,
            item.max_relative_atr,
        )
        for item in EDGE_CANDIDATES
    ) == EXPECTED_CANDIDATES
    assert HORIZONS_BARS == (4, 16, 48)
    assert EVENT_COOLDOWN_BARS == 4
    assert BASE_ROUND_TRIP_COST_BPS == 30.0
    assert SEVERE_ROUND_TRIP_COST_BPS == 70.0
    assert FDR_Q_THRESHOLD == 0.10
    assert MIN_DISCOVERY_EVENTS == 60
    assert MIN_DISCOVERY_DAYS == 20
    assert MIN_DISCOVERY_EVENTS_PER_YEAR == 10
    assert MIN_CHALLENGE_EVENTS == 15


def test_m5_freeze_manifest_matches_protocol_and_preserves_oos_lock() -> None:
    manifest = verify_edge_discovery_freeze()

    assert manifest["cycle"] == EDGE_DISCOVERY_POLICY_NAME
    assert manifest["protocol_sha256"] == EDGE_DISCOVERY_PROTOCOL_SHA256
    assert manifest["candidate_count"] == 24
    assert manifest["hypothesis_test_count"] == 72
    assert manifest["event_cooldown_bars"] == 4
    assert manifest["fdr_q_threshold"] == 0.10
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"


def test_m5_protocol_hash_is_portable_across_line_endings(tmp_path) -> None:
    source = "alpha\nbeta\ngamma\n"
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(source.encode("utf-8"))
    crlf.write_bytes(source.replace("\n", "\r\n").encode("utf-8"))

    assert canonical_text_sha256(lf) == canonical_text_sha256(crlf)
