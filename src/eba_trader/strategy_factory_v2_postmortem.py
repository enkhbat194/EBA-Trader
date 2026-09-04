from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean, median, pstdev
from typing import Any

from .strategy_factory_v2_campaign import (
    PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    PILOT_CAMPAIGN_ID,
)
from .strategy_factory_v2_d0_existing import load_existing_d0_from_inspected_m5
from .strategy_factory_v2_pilot import (
    DEFAULT_WARMUP_BARS,
    LowFidelityCandidateSummary,
    build_low_fidelity_report,
    materialize_low_fidelity_strata,
)

POSTMORTEM_SCHEMA = "sfv2_d0_failure_postmortem_v1"
POSTMORTEM_AUTHORITY = "DISCOVERY_DIAGNOSTIC_ONLY"
INITIAL_CASH = 10_000.0
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.5
ROUND_TRIP_FRICTION_BPS = 2.0 * (FEE_BPS + SLIPPAGE_BPS)
MINIMUM_D0_TRADES = 12
EXPECTED_CANDIDATE_COUNT = 406
EXPECTED_STRATUM_COUNT = 12
EXPECTED_TRIAL_COUNT = EXPECTED_CANDIDATE_COUNT * EXPECTED_STRATUM_COUNT


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _read_json(value: str, *, name: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{name} must be a JSON object")
    return parsed


def _read_ledger(
    path: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    db_path = Path(path).resolve()
    if not db_path.is_file():
        raise RuntimeError("Strategy Factory postmortem research database is missing")
    uri = f"file:{db_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        campaign_row = connection.execute(
            """
            SELECT authority, definition_json
            FROM discovery_campaigns_v2
            WHERE campaign_id = ?
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchone()
        if campaign_row is None:
            raise RuntimeError("Strategy Factory D0 campaign is missing from immutable ledger")
        if str(campaign_row["authority"]) != "DISCOVERY_ONLY":
            raise RuntimeError("Strategy Factory D0 campaign authority drifted")
        campaign_payload = _read_json(
            str(campaign_row["definition_json"]), name="campaign definition"
        )
        definition = campaign_payload.get("definition")
        if not isinstance(definition, dict):
            raise RuntimeError("Strategy Factory D0 campaign definition is invalid")

        candidate_rows = connection.execute(
            """
            SELECT candidate_id, family_id, candidate_spec_sha256, candidate_spec_json,
                   source_code_sha, search_round
            FROM discovery_candidates_v2
            WHERE campaign_id = ?
            ORDER BY family_id, candidate_id
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in candidate_rows:
            item = dict(row)
            item["candidate_spec"] = _read_json(
                str(item.pop("candidate_spec_json")), name="candidate specification"
            )
            candidates.append(item)

        trial_rows = connection.execute(
            """
            SELECT t.trial_id, t.candidate_id, c.family_id, t.dataset_sha256,
                   t.fidelity, t.status, t.metrics_json, t.behavior_json,
                   t.rejection_reason, t.compute_ms
            FROM discovery_trials_v2 AS t
            JOIN discovery_candidates_v2 AS c USING(campaign_id, candidate_id)
            WHERE t.campaign_id = ?
            ORDER BY c.family_id, t.candidate_id, t.fidelity
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchall()
        trials: list[dict[str, Any]] = []
        for row in trial_rows:
            item = dict(row)
            item["metrics"] = _read_json(str(item.pop("metrics_json")), name="trial metrics")
            behavior_json = item.pop("behavior_json")
            item["behavior"] = (
                _read_json(str(behavior_json), name="trial behavior")
                if behavior_json
                else None
            )
            trials.append(item)

        selection_row = connection.execute(
            """
            SELECT selection_id, definition_json, candidate_ids_json
            FROM discovery_survivor_selections_v2
            WHERE campaign_id = ?
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchone()
        if selection_row is None:
            raise RuntimeError("Strategy Factory D0 selection is not frozen")
        selection = {
            "selection_id": str(selection_row["selection_id"]),
            "definition": _read_json(
                str(selection_row["definition_json"]), name="survivor selection definition"
            ),
            "candidate_ids": json.loads(str(selection_row["candidate_ids_json"])),
        }
        if not isinstance(selection["candidate_ids"], list):
            raise RuntimeError("Strategy Factory survivor candidate IDs are invalid")
    finally:
        connection.close()
    return dict(definition), candidates, trials, selection


def _validate_closed_campaign(
    *,
    definition: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    trials: Sequence[Mapping[str, Any]],
    selection: Mapping[str, Any],
    d0_dataset_sha256: str,
    stratum_dataset_sha256: Mapping[str, str],
) -> tuple[str, ...]:
    expected_strata_raw = definition.get("expected_strata")
    if not isinstance(expected_strata_raw, list):
        raise RuntimeError("registered D0 expected strata are missing")
    expected_strata = tuple(str(item) for item in expected_strata_raw)
    if len(expected_strata) != EXPECTED_STRATUM_COUNT:
        raise RuntimeError("postmortem requires the exact completed 12-stratum D0 campaign")
    if len(candidates) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError("postmortem requires the exact completed 406-candidate D0 campaign")
    if len(trials) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError("postmortem requires all 4,872 immutable D0 trials")
    if definition.get("d0_dataset_sha256") != d0_dataset_sha256:
        raise RuntimeError("postmortem D0 dataset does not match registered campaign")
    if selection.get("candidate_ids") != []:
        raise RuntimeError("first Strategy Factory D0 postmortem expects zero frozen survivors")

    registered_mapping = definition.get("stratum_dataset_sha256")
    if not isinstance(registered_mapping, Mapping):
        raise RuntimeError("registered D0 stratum dataset identities are missing")
    normalized_registered = {str(key): str(value) for key, value in registered_mapping.items()}
    if normalized_registered != dict(stratum_dataset_sha256):
        raise RuntimeError("postmortem stratum datasets do not match immutable campaign")

    expected_fidelities = {f"d0-low-v1:{item}" for item in expected_strata}
    seen: set[tuple[str, str]] = set()
    for trial in trials:
        status = str(trial.get("status") or "")
        if status not in {"evaluated", "rejected"}:
            raise RuntimeError("postmortem requires every D0 trial to be terminal")
        candidate_id = str(trial.get("candidate_id") or "")
        fidelity = str(trial.get("fidelity") or "")
        if fidelity not in expected_fidelities:
            raise RuntimeError("postmortem encountered unexpected D0 fidelity")
        pair = (candidate_id, fidelity)
        if pair in seen:
            raise RuntimeError("postmortem encountered duplicate candidate/stratum evidence")
        seen.add(pair)
        stratum_id = fidelity.split(":", 1)[1]
        if str(trial.get("dataset_sha256") or "") != stratum_dataset_sha256[stratum_id]:
            raise RuntimeError("postmortem trial dataset SHA does not match frozen stratum")
    if len(seen) != EXPECTED_TRIAL_COUNT:
        raise RuntimeError("postmortem immutable D0 trial matrix is incomplete")
    return expected_strata


def _ranking_key(item: LowFidelityCandidateSummary) -> tuple[object, ...]:
    benchmark_delta = item.mean_benchmark_relative_return
    expectancy = item.mean_expectancy
    total_return = item.mean_total_return
    max_drawdown = item.mean_max_drawdown
    return (
        -(benchmark_delta if benchmark_delta is not None else float("-inf")),
        -(expectancy if expectancy is not None else float("-inf")),
        -(total_return if total_return is not None else float("-inf")),
        -item.total_trade_count,
        -(max_drawdown if max_drawdown is not None else float("-inf")),
        item.candidate_id,
    )


def _cost_proxies(item: LowFidelityCandidateSummary) -> dict[str, float | None]:
    if item.mean_total_return is None or item.mean_total_cost is None:
        return {
            "costRecoveredReturnProxy": None,
            "feeBurdenReturnProxy": None,
            "slippageBurdenReturnProxy": None,
        }
    friction = FEE_BPS + SLIPPAGE_BPS
    cost_return = item.mean_total_cost / INITIAL_CASH
    return {
        "costRecoveredReturnProxy": item.mean_total_return + cost_return,
        "feeBurdenReturnProxy": cost_return * FEE_BPS / friction,
        "slippageBurdenReturnProxy": cost_return * SLIPPAGE_BPS / friction,
    }


def _candidate_failure_flags(item: LowFidelityCandidateSummary) -> tuple[str, ...]:
    if not item.complete or item.rejected:
        return ("rejected_or_incomplete",)
    flags: list[str] = []
    if item.total_trade_count < MINIMUM_D0_TRADES:
        flags.append("sparse_activity")
    if item.mean_total_return is None or item.mean_total_return <= 0.0:
        flags.append("non_positive_net_return")
    if item.mean_expectancy is None or item.mean_expectancy <= 0.0:
        flags.append("non_positive_expectancy")
    if (
        item.mean_benchmark_relative_return is None
        or item.mean_benchmark_relative_return <= 0.0
    ):
        flags.append("non_positive_benchmark_delta")
    cost = _cost_proxies(item)["costRecoveredReturnProxy"]
    if (
        item.mean_total_return is not None
        and item.mean_total_return <= 0.0
        and cost is not None
        and cost > 0.0
    ):
        flags.append("cost_sensitive_proxy")
    return tuple(flags)


def _parse_trade_key(value: str) -> tuple[int, int, int] | None:
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        entry_ms = int(parts[0])
        exit_ms = int(parts[1])
        side = int(parts[2])
    except ValueError:
        return None
    if side not in {-1, 1} or entry_ms <= 0 or exit_ms <= entry_ms:
        return None
    return entry_ms, exit_ms, side


def _delay_observations(
    *,
    trial: Mapping[str, Any],
    open_by_time: Mapping[int, float],
    step_ms: int,
) -> list[float]:
    behavior = trial.get("behavior")
    if not isinstance(behavior, Mapping):
        return []
    signal_keys = {str(item) for item in behavior.get("signal_keys", ())}
    output: list[float] = []
    for raw_trade in behavior.get("trade_keys", ()):
        parsed = _parse_trade_key(str(raw_trade))
        if parsed is None:
            continue
        entry_ms, _, side = parsed
        signal_ms = entry_ms - step_ms
        signal_key = f"{signal_ms:013d}:{side:+d}"
        if signal_key not in signal_keys:
            continue
        signal_open = open_by_time.get(signal_ms)
        entry_open = open_by_time.get(entry_ms)
        if signal_open is None or entry_open is None or signal_open <= 0.0:
            continue
        output.append(side * (entry_open / signal_open - 1.0) * 10_000.0)
    return output


def _realized_volatility_bps(prices: Sequence[float]) -> float:
    if len(prices) < 3:
        return 0.0
    returns = [math.log(right / left) for left, right in zip(prices, prices[1:], strict=False)]
    return pstdev(returns) * 10_000.0 if len(returns) >= 2 else 0.0


def _build_stratum_descriptors(strata: Sequence[Any]) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    volatilities: list[float] = []
    for item in strata:
        trade_start = item.dataset.trade_start_time_ms
        candles = [
            candle
            for candle in item.dataset.candles
            if trade_start is None or candle.open_time_ms >= trade_start
        ]
        if not candles:
            raise RuntimeError("postmortem stratum has no trade-window candles")
        benchmark = candles[-1].close / candles[0].open - 1.0
        volatility = _realized_volatility_bps([candle.close for candle in candles])
        volatilities.append(volatility)
        raw[item.stratum.stratum_id] = {
            "benchmarkReturn": benchmark,
            "realizedOneBarVolatilityBps": volatility,
            "direction": "UP" if benchmark > 0.0 else "DOWN" if benchmark < 0.0 else "FLAT",
            "openByTime": {candle.open_time_ms: candle.open for candle in item.dataset.candles},
        }
    median_volatility = median(volatilities)
    for value in raw.values():
        value["volatilityBucket"] = (
            "HIGH" if value["realizedOneBarVolatilityBps"] >= median_volatility else "LOW"
        )
    return raw


def _mean_metric(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = [
        value
        for row in rows
        if isinstance(row.get("metrics"), Mapping)
        if (value := _finite(row["metrics"].get(key))) is not None
    ]
    return fmean(values) if values else None


def _sum_trade_count(rows: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for row in rows:
        metrics = row.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        value = _finite(metrics.get("trade_count"))
        if value is not None:
            total += int(value)
    return total


def _regime_summary(
    *,
    family_trials: Sequence[Mapping[str, Any]],
    descriptors: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    by_direction: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_volatility: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for trial in family_trials:
        if str(trial.get("status")) != "evaluated":
            continue
        fidelity = str(trial.get("fidelity") or "")
        stratum_id = fidelity.split(":", 1)[1]
        descriptor = descriptors[stratum_id]
        by_direction[str(descriptor["direction"])].append(trial)
        by_volatility[str(descriptor["volatilityBucket"])].append(trial)

    def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "trialCount": len(rows),
            "meanNetReturn": _mean_metric(rows, "total_return"),
            "meanExpectancy": _mean_metric(rows, "expectancy"),
            "tradeCount": _sum_trade_count(rows),
        }

    return {
        "direction": {key: summarize(value) for key, value in sorted(by_direction.items())},
        "volatility": {
            key: summarize(value) for key, value in sorted(by_volatility.items())
        },
    }


def _primary_diagnosis(
    *,
    summaries: Sequence[LowFidelityCandidateSummary],
) -> str:
    eligible = [item for item in summaries if item.complete and not item.rejected]
    if not eligible:
        return "INACTIVE_OR_REJECTED"
    adequate = [item for item in eligible if item.total_trade_count >= MINIMUM_D0_TRADES]
    if not adequate:
        return "SPARSE_ACTIVITY"
    net_positive = [
        item for item in adequate if item.mean_total_return is not None and item.mean_total_return > 0
    ]
    if not net_positive:
        cost_sensitive = [
            item
            for item in adequate
            if (_cost_proxies(item)["costRecoveredReturnProxy"] or float("-inf")) > 0.0
        ]
        return "COST_SENSITIVE_PROXY" if cost_sensitive else "NEGATIVE_NET_EDGE"
    fully_positive = [
        item
        for item in net_positive
        if item.mean_expectancy is not None
        and item.mean_expectancy > 0.0
        and item.mean_benchmark_relative_return is not None
        and item.mean_benchmark_relative_return > 0.0
    ]
    return "MIXED_ECONOMIC_GATES" if not fully_positive else "DIVERSITY_OR_OTHER_GATE"


def build_sfv2_d0_failure_postmortem(
    *,
    research_db_path: str | Path,
    dataset_root: str | Path,
) -> dict[str, Any]:
    """Explain the closed first D0 campaign without changing research evidence or authority."""

    definition, candidates, trials, selection = _read_ledger(research_db_path)
    declaration, rows, _ = load_existing_d0_from_inspected_m5(dataset_root=dataset_root)
    candles = tuple(row.candle for row in rows)
    strata = materialize_low_fidelity_strata(
        manifest=declaration.manifest,
        candles=candles,
        orderflow_rows=rows,
        warmup_bars=DEFAULT_WARMUP_BARS,
    )
    stratum_dataset_sha256 = {
        item.stratum.stratum_id: item.dataset_sha256 for item in strata
    }
    expected_strata = _validate_closed_campaign(
        definition=definition,
        candidates=candidates,
        trials=trials,
        selection=selection,
        d0_dataset_sha256=declaration.manifest.dataset_sha256,
        stratum_dataset_sha256=stratum_dataset_sha256,
    )
    report = build_low_fidelity_report(
        trials=trials,
        expected_strata=expected_strata,
        behavioral_similarity_threshold=PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    by_family_summary: dict[str, list[LowFidelityCandidateSummary]] = defaultdict(list)
    for item in report.candidates:
        by_family_summary[item.family_id].append(item)
    by_family_trials: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        by_family_trials[str(trial["family_id"])].append(trial)

    descriptors = _build_stratum_descriptors(strata)
    step_ms = 60_000
    family_payloads: list[dict[str, Any]] = []
    global_flags: Counter[str] = Counter()
    all_delay_bps: list[float] = []

    for family_id in sorted(by_family_summary):
        summaries = by_family_summary[family_id]
        family_trials = by_family_trials[family_id]
        complete = [item for item in summaries if item.complete and not item.rejected]
        flag_counts: Counter[str] = Counter()
        for item in summaries:
            flags = _candidate_failure_flags(item)
            flag_counts.update(flags)
            global_flags.update(flags)

        delay_bps: list[float] = []
        for trial in family_trials:
            if str(trial.get("status")) != "evaluated":
                continue
            stratum_id = str(trial["fidelity"]).split(":", 1)[1]
            delay_bps.extend(
                _delay_observations(
                    trial=trial,
                    open_by_time=descriptors[stratum_id]["openByTime"],
                    step_ms=step_ms,
                )
            )
        all_delay_bps.extend(delay_bps)

        ranked = sorted(complete, key=_ranking_key)
        best = ranked[0] if ranked else None
        best_cost = _cost_proxies(best) if best is not None else {}
        cost_sensitive_count = sum(
            "cost_sensitive_proxy" in _candidate_failure_flags(item) for item in complete
        )
        positive_net_count = sum(
            item.mean_total_return is not None and item.mean_total_return > 0.0
            for item in complete
        )
        adequate_activity_count = sum(
            item.total_trade_count >= MINIMUM_D0_TRADES for item in complete
        )
        rejection_reasons = Counter(
            str(item.get("rejection_reason") or "")
            for item in family_trials
            if str(item.get("status")) == "rejected"
        )
        rejection_reasons.pop("", None)

        family_payloads.append(
            {
                "familyId": family_id,
                "candidateCount": len(summaries),
                "completeNonRejectedCandidateCount": len(complete),
                "rejectedOrIncompleteCandidateCount": len(summaries) - len(complete),
                "adequateActivityCandidateCount": adequate_activity_count,
                "positiveNetCandidateCount": positive_net_count,
                "costSensitiveProxyCandidateCount": cost_sensitive_count,
                "primaryDiagnosis": _primary_diagnosis(summaries=summaries),
                "failureFlagCounts": dict(sorted(flag_counts.items())),
                "rejectionReasonCounts": dict(sorted(rejection_reasons.items())),
                "totalTradeCount": sum(item.total_trade_count for item in complete),
                "medianCandidateTradeCount": (
                    median([item.total_trade_count for item in complete]) if complete else None
                ),
                "meanCandidateNetReturn": (
                    fmean([item.mean_total_return for item in complete if item.mean_total_return is not None])
                    if any(item.mean_total_return is not None for item in complete)
                    else None
                ),
                "meanCandidateExpectancy": (
                    fmean([item.mean_expectancy for item in complete if item.mean_expectancy is not None])
                    if any(item.mean_expectancy is not None for item in complete)
                    else None
                ),
                "meanCandidateBenchmarkDelta": (
                    fmean(
                        [
                            item.mean_benchmark_relative_return
                            for item in complete
                            if item.mean_benchmark_relative_return is not None
                        ]
                    )
                    if any(item.mean_benchmark_relative_return is not None for item in complete)
                    else None
                ),
                "meanCandidateTotalCostUsd": (
                    fmean([item.mean_total_cost for item in complete if item.mean_total_cost is not None])
                    if any(item.mean_total_cost is not None for item in complete)
                    else None
                ),
                "bestCandidate": (
                    {
                        "candidateId": best.candidate_id,
                        "meanNetReturn": best.mean_total_return,
                        "meanExpectancy": best.mean_expectancy,
                        "totalTradeCount": best.total_trade_count,
                        "meanBenchmarkDelta": best.mean_benchmark_relative_return,
                        **best_cost,
                        "failureFlags": list(_candidate_failure_flags(best)),
                    }
                    if best is not None
                    else None
                ),
                "recordedCostSensitivityProxy": {
                    "note": "Adds recorded cost attribution back to net return; not a counterfactual fill simulation.",
                    "feeShare": FEE_BPS / (FEE_BPS + SLIPPAGE_BPS),
                    "slippageShare": SLIPPAGE_BPS / (FEE_BPS + SLIPPAGE_BPS),
                },
                "oneBarDelayDiagnostic": {
                    "matchedTradeCount": len(delay_bps),
                    "meanPreEntryDirectionalMoveBps": fmean(delay_bps) if delay_bps else None,
                    "medianPreEntryDirectionalMoveBps": median(delay_bps) if delay_bps else None,
                    "positiveDirectionalMoveShare": (
                        sum(value > 0.0 for value in delay_bps) / len(delay_bps)
                        if delay_bps
                        else None
                    ),
                    "interpretation": (
                        "positive means price moved in the eventual trade direction before next-bar entry"
                    ),
                },
                "regimeDiagnostics": _regime_summary(
                    family_trials=family_trials,
                    descriptors=descriptors,
                ),
            }
        )

    public_descriptors = {
        key: {
            "benchmarkReturn": value["benchmarkReturn"],
            "realizedOneBarVolatilityBps": value["realizedOneBarVolatilityBps"],
            "direction": value["direction"],
            "volatilityBucket": value["volatilityBucket"],
        }
        for key, value in sorted(descriptors.items())
    }
    diagnosis_counts = Counter(item["primaryDiagnosis"] for item in family_payloads)
    return {
        "schema": POSTMORTEM_SCHEMA,
        "authority": POSTMORTEM_AUTHORITY,
        "campaignId": PILOT_CAMPAIGN_ID,
        "sourceCodeSha": definition.get("source_code_sha"),
        "d0DatasetSha256": declaration.manifest.dataset_sha256,
        "selectionId": selection["selection_id"],
        "survivorCount": 0,
        "candidateCount": len(candidates),
        "familyCount": len(by_family_summary),
        "stratumCount": len(strata),
        "terminalTrialCount": len(trials),
        "roundTripFrictionBps": ROUND_TRIP_FRICTION_BPS,
        "initialCash": INITIAL_CASH,
        "failureFlagCounts": dict(sorted(global_flags.items())),
        "familyDiagnosisCounts": dict(sorted(diagnosis_counts.items())),
        "oneBarDelayDiagnostic": {
            "matchedTradeCount": len(all_delay_bps),
            "meanPreEntryDirectionalMoveBps": (
                fmean(all_delay_bps) if all_delay_bps else None
            ),
            "medianPreEntryDirectionalMoveBps": median(all_delay_bps) if all_delay_bps else None,
            "positiveDirectionalMoveShare": (
                sum(value > 0.0 for value in all_delay_bps) / len(all_delay_bps)
                if all_delay_bps
                else None
            ),
        },
        "strata": public_descriptors,
        "families": family_payloads,
        "limitations": [
            "This is inspected D0 discovery evidence and has no confirmation or promotion authority.",
            "Recorded cost sensitivity is an attribution proxy, not a zero-fee/slippage rerun.",
            "The delay diagnostic measures observed pre-entry movement, not counterfactual PnL.",
            "Volatility buckets are descriptive postmortem labels based on the median of 12 D0 strata.",
        ],
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
    }
