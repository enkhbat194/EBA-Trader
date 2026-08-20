from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.m8_alt_data_policy import (
    AUDIT_END_EXCLUSIVE,
    AUDIT_START,
    M8_AUDIT_FREEZE,
    M8_AUDIT_PROTOCOL_SHA256,
    canonical_text_sha256,
    verify_m8_audit_freeze,
)


def test_m8_protocol_hash_is_frozen() -> None:
    assert canonical_text_sha256("docs/M8_ALT_DERIVATIVES_DATA_AUDIT_PROTOCOL.md") == (
        M8_AUDIT_PROTOCOL_SHA256
    )


def test_m8_freeze_manifest_preserves_development_boundary() -> None:
    manifest = verify_m8_audit_freeze()
    assert manifest["status"] == "FROZEN_PRE_AUDIT"
    assert manifest["audit_start"] == AUDIT_START
    assert manifest["audit_end_exclusive"] == AUDIT_END_EXCLUSIVE
    assert manifest["oos_2025"] == "LOCKED_NOT_ACCESSED"
    assert manifest["forward_returns"] == "forbidden"
    assert manifest["strategy_generation"] == "forbidden"
    assert manifest["ai_module"] == "excluded"


def test_m8_freeze_manifest_contains_only_declared_source_families() -> None:
    manifest = json.loads(Path(M8_AUDIT_FREEZE).read_text(encoding="utf-8"))
    assert manifest["primary_sources"] == [
        "binance_usdm_daily_metrics_btcusdt_5m",
        "bybit_linear_btcusdt_1h_kline",
        "bybit_linear_btcusdt_1h_open_interest",
        "bybit_linear_btcusdt_1h_account_ratio",
        "bybit_linear_btcusdt_funding_history",
    ]
    assert manifest["secondary_sources"] == [
        "binance_usdm_daily_bookDepth_btcusdt",
        "binance_usdm_daily_liquidationSnapshot_btcusdt",
    ]


def test_m8_policy_rejects_changed_protocol(tmp_path: Path) -> None:
    protocol = tmp_path / "docs" / "M8_ALT_DERIVATIVES_DATA_AUDIT_PROTOCOL.md"
    freeze = tmp_path / "docs" / "M8_ALT_DERIVATIVES_DATA_AUDIT_FREEZE.json"
    protocol.parent.mkdir(parents=True)
    protocol.write_text("changed\n", encoding="utf-8")
    freeze.write_text(Path(M8_AUDIT_FREEZE).read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed after freeze"):
        verify_m8_audit_freeze(tmp_path)
