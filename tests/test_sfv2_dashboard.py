from __future__ import annotations

import json
from pathlib import Path

from eba_trader.sfv2_dashboard import read_sfv2_d0_summary
from eba_trader.strategy_factory_v2_authorized import STATUS_SCHEMA


def _safe_payload() -> dict[str, object]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": "COMPLETE",
        "requestId": "sfv2-d0-prod-20260901-v1",
        "campaignId": "sfv2-discovery-pilot-v1",
        "authority": "DISCOVERY_ONLY",
        "sourceCodeSha": "a" * 40,
        "candidateCount": 406,
        "stratumCount": 12,
        "expectedTrialCount": 4872,
        "terminalTrialCount": 4872,
        "progressFraction": 1.0,
        "completeCandidateCount": 406,
        "rejectedCandidateCount": 10,
        "behaviorallyEligibleCandidateCount": 100,
        "behavioralClusterCount": 20,
        "selectionFrozen": True,
        "selectionId": "dsel_example",
        "survivorCount": 2,
        "survivorCandidateIds": ["dc_a", "dc_b"],
        "topDiscoveryCandidates": [
            {
                "candidateId": "dc_a",
                "familyId": "compression_expansion_v1",
                "complete": True,
                "rejected": False,
                "eligibleForD0Survivor": True,
                "selectedD0Survivor": True,
                "meanTotalReturn": 0.01,
                "meanExpectancy": 1.2,
                "totalTradeCount": 20,
                "meanBenchmarkRelativeReturn": 0.005,
                "meanMaxDrawdown": -0.02,
                "meanTotalCost": 1.0,
                "meanExposure": 0.1,
                "meanTurnover": 2.0,
                "secret": "must-not-surface",
            }
        ],
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "demoPromotionAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
        "updatedAt": "2026-09-01T12:00:00Z",
    }


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "status.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_dashboard_exposes_only_sanitized_discovery_status(tmp_path: Path) -> None:
    summary = read_sfv2_d0_summary(status_path=_write(tmp_path, _safe_payload()))
    assert summary["available"] is True
    assert summary["phase"] == "COMPLETE"
    assert summary["candidateCount"] == 406
    assert summary["terminalTrialCount"] == 4872
    assert summary["survivorCount"] == 2
    assert summary["d1Opened"] is False
    assert summary["frozenOosOpened"] is False
    assert summary["liveExecutionAllowed"] is False
    assert "secret" not in summary["topDiscoveryCandidates"][0]


def test_dashboard_rejects_any_downstream_authority(tmp_path: Path) -> None:
    payload = _safe_payload()
    payload["d1Opened"] = True
    summary = read_sfv2_d0_summary(status_path=_write(tmp_path, payload))
    assert summary["available"] is False
    assert summary["reason"] == "status_safety_rejected"
