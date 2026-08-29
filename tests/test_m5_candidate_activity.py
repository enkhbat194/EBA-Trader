from __future__ import annotations

from copy import deepcopy

import pytest

from eba_trader.m5_candidate_activity import diagnose_candidate_activity
from eba_trader.m5_multiwindow import REPORT_SCHEMA


def _metrics(
    *,
    trades: int,
    total_return: float,
    expectancy: float = 0.0,
    exposure: float = 0.0,
) -> dict[str, float | int]:
    return {
        "trade_count": trades,
        "total_return": total_return,
        "expectancy": expectancy,
        "exposure": exposure,
    }


def _report() -> dict[str, object]:
    baseline_windows = [
        {
            "windowName": "w1",
            "startMs": 1,
            "endMs": 2,
            "metrics": _metrics(trades=3, total_return=-0.03),
        },
        {
            "windowName": "w2",
            "startMs": 3,
            "endMs": 4,
            "metrics": _metrics(trades=2, total_return=-0.02),
        },
        {
            "windowName": "w3",
            "startMs": 5,
            "endMs": 6,
            "metrics": _metrics(trades=4, total_return=0.01),
        },
    ]
    candidate_windows = [
        {
            "windowName": "w1",
            "startMs": 1,
            "endMs": 2,
            "metrics": _metrics(
                trades=1,
                total_return=0.01,
                expectancy=1.0,
                exposure=0.1,
            ),
        },
        {
            "windowName": "w2",
            "startMs": 3,
            "endMs": 4,
            "metrics": _metrics(trades=0, total_return=0.0),
        },
        {
            "windowName": "w3",
            "startMs": 5,
            "endMs": 6,
            "metrics": _metrics(
                trades=3,
                total_return=-0.01,
                expectancy=-0.5,
                exposure=0.2,
            ),
        },
    ]
    return {
        "schema": REPORT_SCHEMA,
        "evaluationId": "eval_1",
        "materializationId": "mat_1",
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "baseline": {
            "windows": baseline_windows,
            "aggregate": {"totalTradeCount": 9},
        },
        "candidates": [
            {
                "candidateId": "absorption_020",
                "parameters": {"absorption_threshold": 0.2},
                "windows": candidate_windows,
                "aggregate": {"totalTradeCount": 4},
            }
        ],
    }


def test_diagnoses_sparse_entry_filter_activity() -> None:
    result = diagnose_candidate_activity(_report(), candidate_id="absorption_020")

    assert result["activeTradeWindows"] == ["w1", "w3"]
    assert result["activeWindowCount"] == 2
    assert result["zeroTradeWindowCount"] == 1
    assert result["baselineTradeCount"] == 9
    assert result["candidateTradeCount"] == 4
    assert result["candidateTradeRetentionVsBaseline"] == pytest.approx(4 / 9)
    assert result["sampleSufficientForRobustness"] is False
    assert result["diagnosticState"] == "SPARSE_ENTRY_FILTER"
    assert result["structuralRole"] == "ema_crossover_entry_filter"
    assert result["independentSignalGenerator"] is False
    assert result["m5FrozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False

    windows = result["windows"]
    assert isinstance(windows, list)
    assert windows[0]["tradeRetentionRatioVsBaseline"] == pytest.approx(1 / 3)
    assert windows[1]["active"] is False


def test_rejects_opened_frozen_oos() -> None:
    report = _report()
    report["m5FrozenOosOpened"] = True

    with pytest.raises(RuntimeError, match="locked development-only evidence"):
        diagnose_candidate_activity(report, candidate_id="absorption_020")


def test_rejects_trade_total_mismatch() -> None:
    report = deepcopy(_report())
    candidates = report["candidates"]
    assert isinstance(candidates, list)
    candidate = candidates[0]
    assert isinstance(candidate, dict)
    aggregate = candidate["aggregate"]
    assert isinstance(aggregate, dict)
    aggregate["totalTradeCount"] = 99

    with pytest.raises(RuntimeError, match="candidate per-window trade total"):
        diagnose_candidate_activity(report, candidate_id="absorption_020")
