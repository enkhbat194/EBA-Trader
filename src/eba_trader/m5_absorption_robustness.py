from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .m5_multiwindow import (
    M5MultiWindowCandidate,
    M5MultiWindowConfig,
    evaluate_m5_multiwindow,
)
from .research_evidence import canonical_json, sha256_text

REPORT_SCHEMA = "m5_absorption_robustness_report_v1"
CENTER_THRESHOLD = 0.20
MIN_CENTER_TRADES = 30
MIN_BEAT_BASELINE_WINDOWS = 9


@dataclass(frozen=True, slots=True)
class RobustnessScenario:
    scenario_id: str
    group: str
    threshold: float
    config: M5MultiWindowConfig

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenarioId": self.scenario_id,
            "group": self.group,
            "parameters": {"absorption_threshold": self.threshold},
            "config": self.config.as_dict(),
        }


def _scenario(
    scenario_id: str,
    group: str,
    threshold: float = CENTER_THRESHOLD,
    *,
    fast_ema: int = 12,
    slow_ema: int = 26,
    fee_bps: float = 4.0,
    slippage_bps: float = 1.5,
) -> RobustnessScenario:
    return RobustnessScenario(
        scenario_id=scenario_id,
        group=group,
        threshold=threshold,
        config=M5MultiWindowConfig(
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            initial_cash=10_000.0,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        ),
    )


ROBUSTNESS_SCENARIOS = (
    _scenario("threshold_015", "threshold", 0.15),
    _scenario("threshold_018", "threshold", 0.18),
    _scenario("threshold_020", "threshold", 0.20),
    _scenario("threshold_022", "threshold", 0.22),
    _scenario("threshold_025", "threshold", 0.25),
    _scenario("cost_moderate", "cost", fee_bps=6.0, slippage_bps=2.25),
    _scenario("cost_severe", "cost", fee_bps=8.0, slippage_bps=3.0),
    _scenario("ema_faster", "ema", fast_ema=10, slow_ema=24),
    _scenario("ema_slower", "ema", fast_ema=14, slow_ema=30),
)


def _numeric(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"missing numeric robustness metric: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"non-finite robustness metric: {key}")
    return number


def _scenario_result(
    *,
    materialization_manifest: str | Path,
    dataset_root: str | Path,
    scenario: RobustnessScenario,
) -> dict[str, Any]:
    candidate = M5MultiWindowCandidate(
        candidate_id="absorption_020_robustness",
        parameters={"absorption_threshold": scenario.threshold},
    )
    report = evaluate_m5_multiwindow(
        materialization_manifest=materialization_manifest,
        dataset_root=dataset_root,
        candidates=(candidate,),
        config=scenario.config,
    )
    ranking = report.get("developmentRanking")
    baseline = report.get("baseline")
    if not isinstance(ranking, list) or len(ranking) != 1 or not isinstance(ranking[0], dict):
        raise RuntimeError("robustness scenario returned an invalid ranking")
    if not isinstance(baseline, dict) or not isinstance(baseline.get("aggregate"), dict):
        raise RuntimeError("robustness scenario returned an invalid baseline")
    aggregate = ranking[0].get("aggregate")
    if not isinstance(aggregate, dict):
        raise RuntimeError("robustness scenario returned invalid candidate metrics")
    return {
        **scenario.as_dict(),
        "aggregate": aggregate,
        "baselineAggregate": baseline["aggregate"],
    }


def _group_stable(rows: list[dict[str, Any]], group: str) -> bool:
    selected = [row for row in rows if row.get("group") == group]
    if not selected:
        return False
    return all(
        _numeric(row["aggregate"], "meanReturnDeltaVsBaseline") > 0.0
        and _numeric(row["aggregate"], "beatBaselineWindowCount")
        >= MIN_BEAT_BASELINE_WINDOWS
        for row in selected
    )


def evaluate_absorption_robustness(
    *,
    materialization_manifest: str | Path,
    dataset_root: str | Path,
    materialization_id: str,
) -> dict[str, Any]:
    rows = [
        _scenario_result(
            materialization_manifest=materialization_manifest,
            dataset_root=dataset_root,
            scenario=scenario,
        )
        for scenario in ROBUSTNESS_SCENARIOS
    ]
    center = next(row for row in rows if row["scenarioId"] == "threshold_020")
    center_aggregate = center["aggregate"]

    parameter_neighborhood_stable = _group_stable(rows, "threshold")
    cost_stress_stable = _group_stable(rows, "cost")
    ema_stable = _group_stable(rows, "ema")
    center_profitable = (
        _numeric(center_aggregate, "meanReturn") > 0.0
        and _numeric(center_aggregate, "meanExpectancy") > 0.0
    )
    sample_sufficient = _numeric(center_aggregate, "totalTradeCount") >= MIN_CENTER_TRADES
    robustness_verified = all(
        (
            parameter_neighborhood_stable,
            cost_stress_stable,
            ema_stable,
            center_profitable,
            sample_sufficient,
        )
    )

    identity = {
        "schema": REPORT_SCHEMA,
        "materializationId": materialization_id,
        "candidate": {"absorption_threshold": CENTER_THRESHOLD},
        "scenarios": [scenario.as_dict() for scenario in ROBUSTNESS_SCENARIOS],
    }
    robustness_id = f"m5rob_{sha256_text(canonical_json(identity))[:24]}"
    return {
        "schema": REPORT_SCHEMA,
        "robustnessId": robustness_id,
        "materializationId": materialization_id,
        "candidateId": "absorption_020",
        "candidateParameters": {"absorption_threshold": CENTER_THRESHOLD},
        "scenarioCount": len(rows),
        "scenarios": rows,
        "checks": {
            "parameterNeighborhoodStable": parameter_neighborhood_stable,
            "costStressStable": cost_stress_stable,
            "emaStable": ema_stable,
            "centerProfitable": center_profitable,
            "sampleSufficient": sample_sufficient,
            "minimumCenterTrades": MIN_CENTER_TRADES,
            "minimumBeatBaselineWindows": MIN_BEAT_BASELINE_WINDOWS,
        },
        "robustnessVerified": robustness_verified,
        "developmentEvidenceOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def write_immutable_robustness_report(path: str | Path, report: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if output.exists():
        existing = output.read_text(encoding="utf-8")
        if existing != serialized:
            raise RuntimeError("refusing to overwrite immutable robustness report")
        return output
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(output)
    return output
