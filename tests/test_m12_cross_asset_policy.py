from pathlib import Path

from eba_trader.m12_cross_asset_policy import (
    HORIZONS_BARS,
    M12_CANDIDATES,
    M12_PROTOCOL_SHA256,
    canonical_text_sha256,
    verify_m12_freeze,
)


def test_m12_frozen_candidate_surface() -> None:
    assert len(M12_CANDIDATES) == 8
    assert len({item.name for item in M12_CANDIDATES}) == 8
    assert HORIZONS_BARS == (4, 16, 48)
    assert {item.family for item in M12_CANDIDATES} == {
        "impulse",
        "relative",
        "flow_impulse",
    }
    assert sum(item.direction > 0 for item in M12_CANDIDATES) == 4
    assert sum(item.direction < 0 for item in M12_CANDIDATES) == 4


def test_m12_freeze_manifest_verifies() -> None:
    manifest = verify_m12_freeze()
    assert manifest["status"] == "FROZEN_PREDECLARED_NOT_RUN"
    assert manifest["candidate_count"] == 8
    assert manifest["hypothesis_test_count"] == 24
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["parameter_changes_after_first_run"] == "forbidden"


def test_m12_protocol_hash_is_portable_across_newlines(tmp_path: Path) -> None:
    protocol = Path("docs/M12_CROSS_ASSET_ETH_BTC_EDGE_DISCOVERY_PROTOCOL.md")
    text = protocol.read_text(encoding="utf-8")
    crlf = tmp_path / "protocol.md"
    crlf.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert canonical_text_sha256(protocol) == M12_PROTOCOL_SHA256
    assert canonical_text_sha256(crlf) == M12_PROTOCOL_SHA256
