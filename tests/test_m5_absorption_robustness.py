from __future__ import annotations

from pathlib import Path

from eba_trader import m5_absorption_robustness as robustness


def _fake_report(*, mean_return: float, expectancy: float, trades: int) -> dict[str, object]:
    aggregate = {
        "windowCount": 12,
        "meanReturn": mean_return,
        "medianReturn": mean_return,
        "worstWindowReturn": min(mean_return, -0.001),
        "bestWindowReturn": max(mean_return, 0.001),
        "positiveWindowCount": 8 if mean_return > 0 else 2,
        "beatBaselineWindowCount": 10,
        "notWorseThanBaselineWindowCount": 11,
        "meanReturnDeltaVsBaseline": 0.004,
        "medianReturnDeltaVsBaseline": 0.004,
        "worstReturnDeltaVsBaseline": -0.001,
        "bestReturnDeltaVsBaseline": 0.010,
        "meanExpectancy": expectancy,
        "worstMaxDrawdown": -0.003,
        "totalTradeCount": trades,
        "totalCost": 40.0,
    }
    return {
        "baseline": {"aggregate": {"windowCount": 12, "meanReturn": -0.005}},
        "developmentRanking": [{"aggregate": aggregate}],
    }


def test_robustness_scenarios_are_predeclared_and_bounded() -> None:
    scenarios = robustness.ROBUSTNESS_SCENARIOS
    assert len(scenarios) == 9
    assert [item.scenario_id for item in scenarios] == [
        "threshold_015",
        "threshold_018",
        "threshold_020",
        "threshold_022",
        "threshold_025",
        "cost_moderate",
        "cost_severe",
        "ema_faster",
        "ema_slower",
    ]
    threshold_rows = [item for item in scenarios if item.group == "threshold"]
    assert [item.threshold for item in threshold_rows] == [0.15, 0.18, 0.20, 0.22, 0.25]
    assert scenarios[5].config.fee_bps == 6.0
    assert scenarios[5].config.slippage_bps == 2.25
    assert scenarios[6].config.fee_bps == 8.0
    assert scenarios[6].config.slippage_bps == 3.0
    assert scenarios[7].config.fast_ema == 10
    assert scenarios[7].config.slow_ema == 24
    assert scenarios[8].config.fast_ema == 14
    assert scenarios[8].config.slow_ema == 30


def test_robustness_requires_profitability_and_sample_sufficiency(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_evaluate(**kwargs):
        candidate = kwargs["candidates"][0]
        threshold = float(candidate.parameters["absorption_threshold"])
        config = kwargs["config"]
        is_center = (
            threshold == 0.20
            and config.fast_ema == 12
            and config.slow_ema == 26
            and config.fee_bps == 4.0
            and config.slippage_bps == 1.5
        )
        return _fake_report(
            mean_return=-0.0001 if is_center else 0.0002,
            expectancy=-0.9 if is_center else 0.5,
            trades=4 if is_center else 35,
        )

    monkeypatch.setattr(robustness, "evaluate_m5_multiwindow", fake_evaluate)
    report = robustness.evaluate_absorption_robustness(
        materialization_manifest=tmp_path / "manifest.json",
        dataset_root=tmp_path,
        materialization_id="m5corpusmat_test",
    )

    assert report["scenarioCount"] == 9
    assert report["checks"]["parameterNeighborhoodStable"] is True
    assert report["checks"]["costStressStable"] is True
    assert report["checks"]["emaStable"] is True
    assert report["checks"]["centerProfitable"] is False
    assert report["checks"]["sampleSufficient"] is False
    assert report["robustnessVerified"] is False
    assert report["edgeClaimAllowed"] is False
    assert report["promotionAuthority"] is False
    assert report["frozenOosOpened"] is False
    assert report["m5FrozenOosOpened"] is False
    assert report["liveExecutionAllowed"] is False


def test_robustness_can_only_verify_when_every_predeclared_check_passes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        robustness,
        "evaluate_m5_multiwindow",
        lambda **_: _fake_report(mean_return=0.001, expectancy=2.0, trades=35),
    )
    report = robustness.evaluate_absorption_robustness(
        materialization_manifest=tmp_path / "manifest.json",
        dataset_root=tmp_path,
        materialization_id="m5corpusmat_test",
    )

    assert report["checks"]["parameterNeighborhoodStable"] is True
    assert report["checks"]["costStressStable"] is True
    assert report["checks"]["emaStable"] is True
    assert report["checks"]["centerProfitable"] is True
    assert report["checks"]["sampleSufficient"] is True
    assert report["robustnessVerified"] is True
    assert report["edgeClaimAllowed"] is False
    assert report["promotionAuthority"] is False
