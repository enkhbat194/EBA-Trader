from __future__ import annotations

from collections import Counter

from eba_trader.edge_discovery_policy import (
    EDGE_CANDIDATES,
    EDGE_DISCOVERY_POLICY_NAME,
    EDGE_DISCOVERY_PROTOCOL_SHA256,
    HORIZONS_BARS,
    canonical_text_sha256,
    verify_edge_discovery_freeze,
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


def test_m5_freeze_manifest_matches_protocol_and_preserves_oos_lock() -> None:
    manifest = verify_edge_discovery_freeze()

    assert manifest["cycle"] == EDGE_DISCOVERY_POLICY_NAME
    assert manifest["protocol_sha256"] == EDGE_DISCOVERY_PROTOCOL_SHA256
    assert manifest["candidate_count"] == 24
    assert manifest["hypothesis_test_count"] == 72
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"


def test_m5_protocol_hash_is_portable_across_line_endings(tmp_path) -> None:
    source = "alpha\nbeta\ngamma\n"
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(source.encode("utf-8"))
    crlf.write_bytes(source.replace("\n", "\r\n").encode("utf-8"))

    assert canonical_text_sha256(lf) == canonical_text_sha256(crlf)
