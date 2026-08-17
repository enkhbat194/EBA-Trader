from __future__ import annotations

import sys

import pytest

import eba_trader.history as history


def test_generic_downloader_blocks_2025_btc_before_network(monkeypatch, tmp_path) -> None:
    def should_not_fetch(*args, **kwargs):
        pytest.fail("network fetch must not occur for frozen OOS through generic downloader")

    monkeypatch.setattr(history, "fetch_binance_klines", should_not_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eba-download-history",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "1h",
            "--start",
            "2025-01-01",
            "--end",
            "2026-01-01",
            "--out",
            str(tmp_path / "peek.csv"),
        ],
    )
    with pytest.raises(RuntimeError, match="frozen first-cycle BTCUSDT 2025 OOS"):
        history.download_history_cli()
