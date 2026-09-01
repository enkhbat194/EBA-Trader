from __future__ import annotations

from eba_trader.history import Candle
from eba_trader.strategy_factory_v2_d0 import build_d0_dataset_manifest
from eba_trader.strategy_factory_v2_pilot import (
    build_low_fidelity_report,
    materialize_low_fidelity_strata,
)


def _candles(count: int = 24) -> tuple[Candle, ...]:
    output: list[Candle] = []
    for index in range(count):
        open_time = 1_800_000_000_000 + index * 60_000
        price = 100.0 + index
        output.append(
            Candle(
                open_time_ms=open_time,
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.25,
                volume=10.0 + index,
                close_time_ms=open_time + 59_999,
                quote_volume=1000.0 + index,
                trade_count=20 + index,
            )
        )
    return tuple(output)


def _gapped_candles() -> tuple[Candle, ...]:
    first = _candles(6)
    output = list(first)
    second_start = first[-1].close_time_ms + 1 + 3 * 24 * 60 * 60 * 1000
    for index in range(6):
        open_time = second_start + index * 60_000
        price = 200.0 + index
        output.append(
            Candle(
                open_time_ms=open_time,
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.25,
                volume=20.0 + index,
                close_time_ms=open_time + 59_999,
                quote_volume=2000.0 + index,
                trade_count=30 + index,
            )
        )
    return tuple(output)


def _behavior(seed: int) -> dict[str, object]:
    return {
        "signal_keys": [f"{seed:013d}:+1"],
        "trade_keys": [f"{seed:013d}:{seed + 60_000:013d}:+1"],
        "regime_returns": [0.01 * seed, 0.0, 0.0, 0.0],
        "exposure_fraction": 0.25,
        "turnover": 2.0,
    }


def _trial(
    candidate_id: str,
    family_id: str,
    stratum_id: str,
    seed: int,
    *,
    status: str = "evaluated",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "family_id": family_id,
        "fidelity": f"d0-low-v1:{stratum_id}",
        "status": status,
        "metrics": {
            "total_return": 0.01,
            "expectancy": 1.0,
            "trade_count": 2,
            "benchmark_relative_return": 0.005,
            "max_drawdown": -0.01,
            "total_cost": 1.5,
            "exposure": 0.25,
            "turnover_round_trips_per_1000_bars": 2.0,
        },
        "behavior": _behavior(seed) if status == "evaluated" else None,
    }


def test_materialized_strata_cover_declared_d0_and_keep_warmup_context_only() -> None:
    candles = _candles()
    manifest = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        temporal_strata=4,
    )

    strata = materialize_low_fidelity_strata(
        manifest=manifest,
        candles=candles,
        warmup_bars=3,
    )

    assert len(strata) == 4
    assert [item.stratum.stratum_id for item in strata] == [
        "d0-t01",
        "d0-t02",
        "d0-t03",
        "d0-t04",
    ]
    assert strata[0].warmup_start_index == 0
    assert strata[1].warmup_start_index == 3
    assert all(item.dataset.trade_start_time_ms == item.stratum.start_ms for item in strata)
    assert len({item.dataset_sha256 for item in strata}) == 4
    assert all(item.parent_dataset_sha256 == manifest.dataset_sha256 for item in strata)


def test_materialized_strata_never_bridge_multi_day_source_gap_for_warmup() -> None:
    candles = _gapped_candles()
    manifest = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        temporal_strata=2,
    )

    strata = materialize_low_fidelity_strata(
        manifest=manifest,
        candles=candles,
        warmup_bars=3,
    )

    second = strata[1]
    assert second.stratum.start_index == 6
    assert second.warmup_start_index == second.stratum.start_index
    assert second.dataset.candles[0].open_time_ms == second.stratum.start_ms


def test_materialization_rejects_manifest_content_mismatch() -> None:
    candles = _candles()
    manifest = build_d0_dataset_manifest(
        symbol="BTCUSDT",
        venue="usd_m_futures",
        interval="1m",
        candles=candles,
        temporal_strata=4,
    )
    changed = list(candles)
    original = changed[5]
    changed[5] = Candle(
        open_time_ms=original.open_time_ms,
        open=original.open,
        high=original.high,
        low=original.low,
        close=original.close + 1.0,
        volume=original.volume,
        close_time_ms=original.close_time_ms,
        quote_volume=original.quote_volume,
        trade_count=original.trade_count,
    )

    try:
        materialize_low_fidelity_strata(
            manifest=manifest,
            candles=tuple(changed),
            warmup_bars=3,
        )
    except ValueError as exc:
        assert "does not match supplied dataset content" in str(exc)
    else:
        raise AssertionError("content mismatch must fail closed")


def test_report_requires_all_strata_before_behavioral_representative_selection() -> None:
    expected = ("d0-t01", "d0-t02")
    trials = [
        _trial("a", "family-a", "d0-t01", 1),
        _trial("a", "family-a", "d0-t02", 2),
        _trial("b", "family-a", "d0-t01", 1),
    ]

    report = build_low_fidelity_report(trials=trials, expected_strata=expected)
    by_id = {item.candidate_id: item for item in report.candidates}

    assert by_id["a"].complete is True
    assert by_id["a"].total_trade_count == 4
    assert by_id["b"].complete is False
    assert report.complete_candidate_count == 1
    assert report.representative_candidate_ids == ("a",)


def test_rejected_candidate_never_enters_behavioral_representatives() -> None:
    expected = ("d0-t01", "d0-t02")
    trials = [
        _trial("a", "family-a", "d0-t01", 1),
        _trial("a", "family-a", "d0-t02", 2),
        _trial("b", "family-b", "d0-t01", 3),
        _trial("b", "family-b", "d0-t02", 4, status="rejected"),
    ]

    report = build_low_fidelity_report(trials=trials, expected_strata=expected)
    by_id = {item.candidate_id: item for item in report.candidates}

    assert by_id["b"].complete is True
    assert by_id["b"].rejected is True
    assert report.rejected_candidate_count == 1
    assert report.representative_candidate_ids == ("a",)


def test_behavioral_near_duplicates_collapse_after_full_stratified_coverage() -> None:
    expected = ("d0-t01", "d0-t02")
    trials = [
        _trial("a", "family-a", "d0-t01", 1),
        _trial("a", "family-a", "d0-t02", 2),
        _trial("b", "family-b", "d0-t01", 1),
        _trial("b", "family-b", "d0-t02", 2),
    ]

    report = build_low_fidelity_report(
        trials=trials,
        expected_strata=expected,
        behavioral_similarity_threshold=0.90,
    )

    assert report.complete_candidate_count == 2
    assert report.representative_candidate_ids == ("a",)
