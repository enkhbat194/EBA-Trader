from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.sf2_development import _aggregate
from eba_trader.sf3_development import (
    BASELINE_ID,
    DEVELOPMENT_REPORT_SCHEMA,
    candidate_set_sha256,
    validate_sf3_development,
)
from eba_trader.sf3_protocol import load_sf3_protocol

PROTOCOL_PATH = Path("config/sf3_research_protocol_v1.json")


def _metrics(total_return: float, *, expectancy: float, trades: int) -> dict[str, float | int]:
    return {
        "total_return": total_return,
        "expectancy": expectancy,
        "max_drawdown": min(total_return, 0.0),
        "trade_count": trades,
        "total_cost": 1.0,
    }


def _report(first_returns: list[float]) -> dict[str, object]:
    protocol = load_sf3_protocol(PROTOCOL_PATH)
    names = [window.name for window in protocol.corpus.windows]
    baseline_windows = [
        {"windowName": name, "metrics": _metrics(0.0, expectancy=0.0, trades=1)}
        for name in names
    ]
    baseline_by_name = {row["windowName"]: row for row in baseline_windows}
    candidates: list[dict[str, object]] = []
    for index, candidate in enumerate(protocol.candidates):
        returns = first_returns if index == 0 else [-0.01] * 12
        expectancy = 1.0 if index == 0 else -1.0
        windows = [
            {
                "windowName": name,
                "metrics": _metrics(value, expectancy=expectancy, trades=3),
            }
            for name, value in zip(names, returns, strict=True)
        ]
        candidates.append(
            {
                "candidateId": candidate.candidate_id,
                "family": candidate.family,
                "parameters": dict(candidate.parameters),
                "aggregate": _aggregate(windows, baseline_by_name),
                "windows": windows,
            }
        )
    ranking = [
        {"candidateId": candidate.candidate_id}
        for candidate in protocol.candidates
    ]
    return {
        "schema": DEVELOPMENT_REPORT_SCHEMA,
        "evaluationId": "sf3dev_test",
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": "sf3mat_test",
        "candidateSetSha256": candidate_set_sha256(protocol),
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "baseline": {
            "baselineId": BASELINE_ID,
            "windows": baseline_windows,
        },
        "candidates": candidates,
        "developmentRanking": ranking,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def test_all_positive_sf3_windows_survive_conservative_48_budget() -> None:
    report = _report([0.01] * 12)
    result = validate_sf3_development(report, protocol_path=PROTOCOL_PATH)

    assert result["validationState"] == "VERIFIED_CANDIDATE_AVAILABLE"
    assert result["verifiedCandidateCount"] == 1
    assert result["topVerifiedCandidate"] == "s3_rft_l08"
    first = result["candidateValidation"][0]
    assert first["rawPValue"] == pytest.approx(1 / 4096)
    assert first["adjustedPValue"] == pytest.approx(48 / 4096)
    assert first["verifiedForRobustness"] is True
    assert result["frozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False


def test_eleven_positive_sf3_windows_fail_bonferroni_significance() -> None:
    report = _report([0.01] * 11 + [-0.01])
    result = validate_sf3_development(report, protocol_path=PROTOCOL_PATH)

    assert result["validationState"] == "NO_VERIFIED_CANDIDATE"
    first = result["candidateValidation"][0]
    assert first["qualified"] is True
    assert first["rawPValue"] == pytest.approx(13 / 4096)
    assert first["adjustedPValue"] == pytest.approx(13 * 48 / 4096)
    assert first["verifiedForRobustness"] is False
    assert "statisticalSignificance" in first["failedChecks"]


def test_sf3_rejects_tampered_aggregate() -> None:
    report = _report([0.01] * 12)
    report["candidates"][0]["aggregate"]["meanReturn"] = 999.0

    with pytest.raises(RuntimeError, match="aggregate mismatch"):
        validate_sf3_development(report, protocol_path=PROTOCOL_PATH)


def test_sf3_rejects_unsafe_development_report() -> None:
    report = _report([0.01] * 12)
    report["liveExecutionAllowed"] = True

    with pytest.raises(RuntimeError, match="unsafe SF3 development report"):
        validate_sf3_development(report, protocol_path=PROTOCOL_PATH)
