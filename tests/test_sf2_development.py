from __future__ import annotations

from pathlib import Path

import pytest

from eba_trader.sf2_development import (
    BASELINE_FAST_EMA,
    BASELINE_ID,
    BASELINE_SLOW_EMA,
    DEVELOPMENT_REPORT_SCHEMA,
    FEE_BPS,
    INITIAL_CASH,
    SLIPPAGE_BPS,
    candidate_set_sha256,
    validate_sf2_development,
)
from eba_trader.sf2_protocol import load_sf2_protocol

PROTOCOL_PATH = Path("config/sf2_research_protocol_v1.json")


def _report(first_returns: list[float]) -> dict[str, object]:
    protocol = load_sf2_protocol(PROTOCOL_PATH)
    names = [window.name for window in protocol.corpus.windows]
    baseline_windows = [
        {"windowName": name, "metrics": {"total_return": 0.0}}
        for name in names
    ]
    candidates: list[dict[str, object]] = []
    for index, candidate in enumerate(protocol.candidates):
        returns = first_returns if index == 0 else [-0.01] * 12
        positive = sum(value > 0.0 for value in returns)
        candidates.append(
            {
                "candidateId": candidate.candidate_id,
                "family": candidate.family,
                "parameters": dict(candidate.parameters),
                "aggregate": {
                    "meanReturn": sum(returns) / len(returns),
                    "meanExpectancy": 1.0 if index == 0 else -1.0,
                    "totalTradeCount": 30,
                    "beatBaselineWindowCount": positive,
                },
                "windows": [
                    {"windowName": name, "metrics": {"total_return": value}}
                    for name, value in zip(names, returns, strict=True)
                ],
            }
        )
    ranking = [
        {"candidateId": candidate.candidate_id}
        for candidate in protocol.candidates
    ]
    return {
        "schema": DEVELOPMENT_REPORT_SCHEMA,
        "evaluationId": "sf2dev_test",
        "phaseId": protocol.phase_id,
        "protocolId": protocol.protocol_id,
        "materializationId": "sf2mat_test",
        "candidateSetSha256": candidate_set_sha256(protocol),
        "candidateCount": 24,
        "multipleTestingBudget": 48,
        "windowCount": 12,
        "baseline": {
            "baselineId": BASELINE_ID,
            "adapter": "ema_feature_baseline_v1",
            "parameters": {
                "fastEma": BASELINE_FAST_EMA,
                "slowEma": BASELINE_SLOW_EMA,
                "initialCash": INITIAL_CASH,
                "feeBps": FEE_BPS,
                "slippageBps": SLIPPAGE_BPS,
            },
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


def test_all_positive_windows_survive_conservative_48_budget() -> None:
    report = _report([0.01] * 12)
    result = validate_sf2_development(report, protocol_path=PROTOCOL_PATH)

    assert result["validationState"] == "VERIFIED_CANDIDATE_AVAILABLE"
    assert result["verifiedCandidateCount"] == 1
    assert result["topVerifiedCandidate"] == "s2_div_l001"
    first = result["candidateValidation"][0]
    assert first["rawPValue"] == pytest.approx(1 / 4096)
    assert first["adjustedPValue"] == pytest.approx(48 / 4096)
    assert first["verifiedForRobustness"] is True
    assert result["frozenOosOpened"] is False
    assert result["liveExecutionAllowed"] is False


def test_eleven_positive_windows_fail_bonferroni_significance() -> None:
    report = _report([0.01] * 11 + [-0.01])
    result = validate_sf2_development(report, protocol_path=PROTOCOL_PATH)

    assert result["validationState"] == "NO_VERIFIED_CANDIDATE"
    assert result["verifiedCandidateCount"] == 0
    first = result["candidateValidation"][0]
    assert first["qualified"] is True
    assert first["rawPValue"] == pytest.approx(13 / 4096)
    assert first["adjustedPValue"] == pytest.approx(13 * 48 / 4096)
    assert first["verifiedForRobustness"] is False
    assert "statisticalSignificance" in first["failedChecks"]


def test_unsafe_development_report_is_rejected() -> None:
    report = _report([0.01] * 12)
    report["liveExecutionAllowed"] = True

    with pytest.raises(RuntimeError, match="unsafe SF2 development report"):
        validate_sf2_development(report, protocol_path=PROTOCOL_PATH)


def test_candidate_parameter_tampering_is_rejected() -> None:
    report = _report([0.01] * 12)
    candidates = report["candidates"]
    assert isinstance(candidates, list)
    first = candidates[0]
    assert isinstance(first, dict)
    parameters = first["parameters"]
    assert isinstance(parameters, dict)
    parameters["signal_threshold"] = 0.999

    with pytest.raises(RuntimeError, match="candidate parameter mismatch"):
        validate_sf2_development(report, protocol_path=PROTOCOL_PATH)
