from __future__ import annotations

from eba_trader import m8_alt_data_audit as core
from eba_trader.history import parse_utc
from eba_trader.m8_alt_data_runner import parse_binance_metrics_rows_with_frozen_boundary


def _row(timestamp: str, *, oi: str = "100", taker_ratio: str = "1.05") -> list[str]:
    return [
        timestamp,
        "BTCUSDT",
        oi,
        "1000000",
        "1.1",
        "1.2",
        "1.0",
        taker_ratio,
    ]


def test_frozen_boundary_adapter_discards_exact_start_only() -> None:
    header = list(core.METRICS_COLUMNS)
    start = parse_utc("2021-01-01T00:00:00Z")
    end = parse_utc("2021-01-01T00:10:00Z")
    rows, exact, conflicting = parse_binance_metrics_rows_with_frozen_boundary(
        [
            header,
            _row("2021-01-01 00:00:00"),
            _row("2021-01-01 00:05:00"),
        ],
        start_ms=start,
        end_ms=end,
    )
    assert [item.timestamp_ms for item in rows] == [start + core.FIVE_MIN_MS]
    assert exact == 0
    assert conflicting == 0


def test_frozen_boundary_adapter_preserves_non_boundary_conflict_detection() -> None:
    header = list(core.METRICS_COLUMNS)
    start = parse_utc("2021-01-01T00:00:00Z")
    end = parse_utc("2021-01-01T00:10:00Z")
    rows, exact, conflicting = parse_binance_metrics_rows_with_frozen_boundary(
        [
            header,
            _row("2021-01-01 00:05:00"),
            _row("2021-01-01 00:05:00", oi="101"),
        ],
        start_ms=start,
        end_ms=end,
    )
    assert len(rows) == 1
    assert exact == 0
    assert conflicting == 1


def test_frozen_boundary_adapter_does_not_recurse_when_core_parser_is_patched(monkeypatch) -> None:
    header = list(core.METRICS_COLUMNS)
    start = parse_utc("2021-01-01T00:00:00Z")
    end = parse_utc("2021-01-01T00:10:00Z")
    monkeypatch.setattr(
        core,
        "parse_binance_metrics_rows",
        parse_binance_metrics_rows_with_frozen_boundary,
    )
    rows, exact, conflicting = parse_binance_metrics_rows_with_frozen_boundary(
        [header, _row("2021-01-01 00:05:00")],
        start_ms=start,
        end_ms=end,
    )
    assert [item.timestamp_ms for item in rows] == [start + core.FIVE_MIN_MS]
    assert exact == 0
    assert conflicting == 0


def test_malformed_metric_value_becomes_explicit_nonpositive_audit_failure() -> None:
    header = list(core.METRICS_COLUMNS)
    start = parse_utc("2021-01-01T00:00:00Z")
    end = parse_utc("2021-01-01T00:10:00Z")
    rows, exact, conflicting = parse_binance_metrics_rows_with_frozen_boundary(
        [header, _row("2021-01-01 00:05:00", taker_ratio="")],
        start_ms=start,
        end_ms=end,
    )
    assert len(rows) == 1
    assert rows[0].sum_taker_long_short_vol_ratio == 0.0
    report = core.audit_binance_metrics(rows)
    assert report["status"] == "FAIL"
    assert report["all_metric_fields_finite_and_positive"] is False
    assert exact == 0
    assert conflicting == 0
