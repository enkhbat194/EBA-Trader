from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .research_store import ResearchStore
from .strategy_discovery_v2 import MAX_SURVIVORS, DiscoveryTrialLedger
from .strategy_factory_v2_campaign import (
    PILOT_AUTHORITY,
    PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    PILOT_CAMPAIGN_ID,
    D0PilotCampaignRun,
    freeze_d0_pilot_survivors,
    run_existing_production_d0_pilot,
)
from .strategy_factory_v2_pilot import LowFidelityCandidateSummary

AUTHORIZATION_SCHEMA = "sfv2_d0_production_authorization_v1"
SELECTION_POLICY_SCHEMA = "sfv2_d0_survivor_policy_v1"
STATUS_SCHEMA = "sfv2_d0_production_status_v1"
EXPECTED_REQUEST_ID = "sfv2-d0-prod-20260901-v1"
EXPECTED_SOURCE_KIND = "INSPECTED_M5_DEVELOPMENT_CORPUS"
EXPECTED_PROVENANCE_CLASS = "INSPECTED_REUSABLE_DISCOVERY_DATA"
EXPECTED_DECLARATION_SHA256 = (
    "88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c"
)
EXPECTED_DATASET_SHA256 = (
    "aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb"
)
EXPECTED_CANDIDATE_COUNT = 406
EXPECTED_STRATUM_COUNT = 12
EXPECTED_MINIMUM_TOTAL_TRADES = 12
EXPECTED_RANKING_ORDER = (
    "mean_benchmark_relative_return_desc",
    "mean_expectancy_desc",
    "mean_total_return_desc",
    "total_trade_count_desc",
    "mean_max_drawdown_desc",
    "candidate_id_asc",
)
DEFAULT_STATUS_PATH = Path("/var/lib/eba-trader/research/sfv2-d0-pilot-status.json")


@dataclass(frozen=True, slots=True)
class Sfv2D0Authorization:
    request_id: str
    max_compute_ms_per_stratum: int
    max_cycles_per_invocation: int
    minimum_total_trades: int
    maximum_survivors: int
    selection_policy: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class AuthorizedD0CycleResult:
    phase: str
    campaign_run: D0PilotCampaignRun
    terminal_trial_count: int
    expected_trial_count: int
    selection_id: str | None
    survivor_candidate_ids: tuple[str, ...]
    status_payload: Mapping[str, object]


def load_sfv2_d0_authorization(path: str | Path) -> Sfv2D0Authorization:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read SFv2 D0 production authorization") from exc
    if not isinstance(payload, dict):
        raise ValueError("SFv2 D0 production authorization must be a JSON object")

    required = {
        "schema",
        "request_id",
        "enabled",
        "single_use",
        "campaign_id",
        "authority",
        "authorization_basis",
        "expected_d0_source_kind",
        "expected_d0_provenance_class",
        "expected_d0_declaration_sha256",
        "expected_d0_dataset_sha256",
        "expected_candidate_count",
        "expected_stratum_count",
        "behavioral_similarity_threshold",
        "runtime",
        "selection_policy",
        "safety",
    }
    if set(payload) != required:
        raise ValueError("SFv2 D0 authorization fields changed")
    if payload["schema"] != AUTHORIZATION_SCHEMA:
        raise ValueError("unsupported SFv2 D0 authorization schema")
    if payload["request_id"] != EXPECTED_REQUEST_ID:
        raise ValueError("SFv2 D0 authorization request identity changed")
    if payload["enabled"] is not True or payload["single_use"] is not True:
        raise ValueError("SFv2 D0 authorization must remain enabled and single-use")
    if payload["campaign_id"] != PILOT_CAMPAIGN_ID or payload["authority"] != PILOT_AUTHORITY:
        raise ValueError("SFv2 D0 authorization campaign identity changed")
    if payload["authorization_basis"] != "explicit_repository_owner_request_2026-09-01":
        raise ValueError("SFv2 D0 authorization basis changed")
    if payload["expected_d0_source_kind"] != EXPECTED_SOURCE_KIND:
        raise ValueError("SFv2 D0 authorized source kind changed")
    if payload["expected_d0_provenance_class"] != EXPECTED_PROVENANCE_CLASS:
        raise ValueError("SFv2 D0 authorized provenance class changed")
    if payload["expected_d0_declaration_sha256"] != EXPECTED_DECLARATION_SHA256:
        raise ValueError("SFv2 D0 authorized declaration SHA changed")
    if payload["expected_d0_dataset_sha256"] != EXPECTED_DATASET_SHA256:
        raise ValueError("SFv2 D0 authorized dataset SHA changed")
    if payload["expected_candidate_count"] != EXPECTED_CANDIDATE_COUNT:
        raise ValueError("SFv2 D0 authorized candidate count changed")
    if payload["expected_stratum_count"] != EXPECTED_STRATUM_COUNT:
        raise ValueError("SFv2 D0 authorized stratum count changed")
    if payload["behavioral_similarity_threshold"] != PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD:
        raise ValueError("SFv2 D0 behavioral similarity threshold changed")

    runtime = payload["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "max_compute_ms_per_stratum",
        "max_cycles_per_invocation",
    }:
        raise ValueError("SFv2 D0 runtime authorization changed")
    max_compute = runtime["max_compute_ms_per_stratum"]
    max_cycles = runtime["max_cycles_per_invocation"]
    if isinstance(max_compute, bool) or not isinstance(max_compute, int) or max_compute != 30000:
        raise ValueError("SFv2 D0 compute budget changed")
    if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or max_cycles != 4:
        raise ValueError("SFv2 D0 cycle budget changed")

    policy = payload["selection_policy"]
    if not isinstance(policy, dict):
        raise ValueError("SFv2 D0 selection policy is invalid")
    expected_policy_keys = {
        "schema",
        "minimum_mean_total_return_exclusive",
        "minimum_mean_expectancy_exclusive",
        "minimum_mean_benchmark_relative_return_exclusive",
        "minimum_total_trades",
        "one_per_behavioral_cluster",
        "maximum_survivors",
        "ranking_order",
    }
    if set(policy) != expected_policy_keys:
        raise ValueError("SFv2 D0 selection policy fields changed")
    if policy["schema"] != SELECTION_POLICY_SCHEMA:
        raise ValueError("unsupported SFv2 D0 selection policy schema")
    for key in (
        "minimum_mean_total_return_exclusive",
        "minimum_mean_expectancy_exclusive",
        "minimum_mean_benchmark_relative_return_exclusive",
    ):
        if policy[key] != 0.0:
            raise ValueError(f"SFv2 D0 economic gate changed: {key}")
    if policy["minimum_total_trades"] != EXPECTED_MINIMUM_TOTAL_TRADES:
        raise ValueError("SFv2 D0 activity floor changed")
    if policy["one_per_behavioral_cluster"] is not True:
        raise ValueError("SFv2 D0 cluster-diversity rule changed")
    if policy["maximum_survivors"] != MAX_SURVIVORS:
        raise ValueError("SFv2 D0 survivor cap changed")
    if tuple(policy["ranking_order"]) != EXPECTED_RANKING_ORDER:
        raise ValueError("SFv2 D0 deterministic ranking order changed")

    safety = payload["safety"]
    expected_safety = {
        "fresh_confirmation_evidence": False,
        "verification_authority": False,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
        "public_trigger_allowed": False,
    }
    if safety != expected_safety:
        raise ValueError("SFv2 D0 safety authorization changed")

    return Sfv2D0Authorization(
        request_id=EXPECTED_REQUEST_ID,
        max_compute_ms_per_stratum=max_compute,
        max_cycles_per_invocation=max_cycles,
        minimum_total_trades=EXPECTED_MINIMUM_TOTAL_TRADES,
        maximum_survivors=MAX_SURVIVORS,
        selection_policy=dict(policy),
    )


def _finite(value: float | int | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def is_d0_survivor_eligible(
    item: LowFidelityCandidateSummary,
    *,
    minimum_total_trades: int = EXPECTED_MINIMUM_TOTAL_TRADES,
) -> bool:
    total_return = _finite(item.mean_total_return)
    expectancy = _finite(item.mean_expectancy)
    benchmark_delta = _finite(item.mean_benchmark_relative_return)
    return bool(
        item.complete
        and not item.rejected
        and item.behavior is not None
        and total_return is not None
        and total_return > 0.0
        and expectancy is not None
        and expectancy > 0.0
        and benchmark_delta is not None
        and benchmark_delta > 0.0
        and item.total_trade_count >= minimum_total_trades
    )


def _ranking_key(item: LowFidelityCandidateSummary) -> tuple[object, ...]:
    benchmark_delta = _finite(item.mean_benchmark_relative_return)
    expectancy = _finite(item.mean_expectancy)
    total_return = _finite(item.mean_total_return)
    max_drawdown = _finite(item.mean_max_drawdown)
    return (
        -(benchmark_delta if benchmark_delta is not None else float("-inf")),
        -(expectancy if expectancy is not None else float("-inf")),
        -(total_return if total_return is not None else float("-inf")),
        -int(item.total_trade_count),
        -(max_drawdown if max_drawdown is not None else float("-inf")),
        item.candidate_id,
    )


def select_d0_pilot_survivors(
    campaign_run: D0PilotCampaignRun,
    *,
    minimum_total_trades: int = EXPECTED_MINIMUM_TOTAL_TRADES,
    maximum_survivors: int = MAX_SURVIVORS,
) -> tuple[str, ...]:
    """Choose D0 nominations deterministically without granting verification authority.

    Negative economics cannot be rescued by behavioral novelty. Within each behavioral cluster,
    only economically positive candidates with a modest D0 activity floor are considered and the
    strongest member is chosen by a preregistered lexicographic ranking. The final verification
    pipeline still retains its independent >=30-trade and statistical gates.
    """

    if not 1 <= maximum_survivors <= MAX_SURVIVORS:
        raise ValueError("maximum_survivors exceeds Strategy Factory v2 cap")
    by_id = {item.candidate_id: item for item in campaign_run.report.candidates}
    cluster_winners: list[LowFidelityCandidateSummary] = []
    for cluster in campaign_run.accounting.clusters:
        viable = [
            by_id[candidate_id]
            for candidate_id in cluster.member_candidate_ids
            if candidate_id in by_id
            and is_d0_survivor_eligible(
                by_id[candidate_id], minimum_total_trades=minimum_total_trades
            )
        ]
        if not viable:
            continue
        cluster_winners.append(min(viable, key=_ranking_key))
    selected = sorted(cluster_winners, key=_ranking_key)[:maximum_survivors]
    return tuple(item.candidate_id for item in selected)


def _candidate_public_summary(
    item: LowFidelityCandidateSummary,
    *,
    selected: set[str],
    minimum_total_trades: int,
) -> dict[str, object]:
    return {
        "candidateId": item.candidate_id,
        "familyId": item.family_id,
        "complete": item.complete,
        "rejected": item.rejected,
        "eligibleForD0Survivor": is_d0_survivor_eligible(
            item, minimum_total_trades=minimum_total_trades
        ),
        "selectedD0Survivor": item.candidate_id in selected,
        "meanTotalReturn": item.mean_total_return,
        "meanExpectancy": item.mean_expectancy,
        "totalTradeCount": item.total_trade_count,
        "meanBenchmarkRelativeReturn": item.mean_benchmark_relative_return,
        "meanMaxDrawdown": item.mean_max_drawdown,
        "meanTotalCost": item.mean_total_cost,
        "meanExposure": item.mean_exposure,
        "meanTurnover": item.mean_turnover,
    }


def _terminal_trial_count(ledger: DiscoveryTrialLedger) -> int:
    return sum(
        str(item.get("status")) in {"evaluated", "rejected"}
        and str(item.get("fidelity") or "").startswith("d0-low-v1:")
        for item in ledger.list_trials(PILOT_CAMPAIGN_ID)
    )


def _build_status_payload(
    *,
    authorization: Sfv2D0Authorization,
    campaign_run: D0PilotCampaignRun,
    terminal_trial_count: int,
    selection_id: str | None,
    survivor_candidate_ids: tuple[str, ...],
) -> dict[str, object]:
    expected_trial_count = campaign_run.candidate_count * campaign_run.stratum_count
    complete = (
        campaign_run.report.complete_candidate_count == campaign_run.candidate_count
        and terminal_trial_count == expected_trial_count
        and selection_id is not None
    )
    selected = set(survivor_candidate_ids)
    ranked = sorted(
        (
            item
            for item in campaign_run.report.candidates
            if item.complete and not item.rejected and item.behavior is not None
        ),
        key=_ranking_key,
    )
    top = [
        _candidate_public_summary(
            item,
            selected=selected,
            minimum_total_trades=authorization.minimum_total_trades,
        )
        for item in ranked[:10]
    ]
    return {
        "schema": STATUS_SCHEMA,
        "phase": "COMPLETE" if complete else "IN_PROGRESS",
        "requestId": authorization.request_id,
        "campaignId": campaign_run.campaign_id,
        "authority": PILOT_AUTHORITY,
        "sourceCodeSha": campaign_run.source_code_sha,
        "d0DeclarationSha256": campaign_run.d0_declaration_sha256,
        "d0DatasetSha256": campaign_run.d0_dataset_sha256,
        "candidateCount": campaign_run.candidate_count,
        "stratumCount": campaign_run.stratum_count,
        "expectedTrialCount": expected_trial_count,
        "terminalTrialCount": terminal_trial_count,
        "progressFraction": (
            terminal_trial_count / expected_trial_count if expected_trial_count else 0.0
        ),
        "completeCandidateCount": campaign_run.accounting.complete_candidate_count,
        "rejectedCandidateCount": campaign_run.accounting.rejected_candidate_count,
        "behaviorallyEligibleCandidateCount": (
            campaign_run.accounting.behaviorally_eligible_candidate_count
        ),
        "behavioralClusterCount": campaign_run.accounting.behavioral_cluster_count,
        "newlyEvaluatedTrialCount": campaign_run.newly_evaluated_trial_count,
        "reusedTerminalTrialCount": campaign_run.reused_terminal_trial_count,
        "stoppedForComputeBudget": campaign_run.stopped_for_compute_budget,
        "selectionFrozen": selection_id is not None,
        "selectionId": selection_id,
        "survivorCount": len(survivor_candidate_ids),
        "survivorCandidateIds": list(survivor_candidate_ids),
        "topDiscoveryCandidates": top,
        "selectionPolicy": dict(authorization.selection_policy),
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "demoPromotionAllowed": False,
        "liveExecutionAllowed": False,
        "realExecutionAllowed": False,
        "updatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def write_sfv2_d0_status(
    payload: Mapping[str, object],
    *,
    path: str | Path | None = None,
) -> None:
    target = Path(
        path
        or os.getenv("EBA_SFV2_D0_STATUS_PATH", "").strip()
        or DEFAULT_STATUS_PATH
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, target)


def run_authorized_d0_cycle(
    *,
    authorization_path: str | Path,
    dataset_root: str | Path,
    research_db_path: str | Path,
    repo_root: str | Path,
    status_path: str | Path | None = None,
) -> AuthorizedD0CycleResult:
    authorization = load_sfv2_d0_authorization(authorization_path)
    campaign_run = run_existing_production_d0_pilot(
        dataset_root=dataset_root,
        research_db_path=research_db_path,
        repo_root=repo_root,
        max_compute_ms_per_stratum=authorization.max_compute_ms_per_stratum,
    )
    if campaign_run.authority != PILOT_AUTHORITY:
        raise RuntimeError("authorized D0 run lost DISCOVERY_ONLY authority")
    if campaign_run.d0_declaration_sha256 != EXPECTED_DECLARATION_SHA256:
        raise RuntimeError("authorized D0 run declaration SHA changed")
    if campaign_run.d0_dataset_sha256 != EXPECTED_DATASET_SHA256:
        raise RuntimeError("authorized D0 run dataset SHA changed")
    if campaign_run.candidate_count != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError("authorized D0 run candidate count changed")
    if campaign_run.stratum_count != EXPECTED_STRATUM_COUNT:
        raise RuntimeError("authorized D0 run stratum count changed")
    if (
        campaign_run.d1_opened
        or campaign_run.frozen_oos_opened
        or campaign_run.live_execution_allowed
    ):
        raise RuntimeError("authorized D0 run attempted downstream authority")

    ledger = DiscoveryTrialLedger(ResearchStore(research_db_path))
    terminal_trial_count = _terminal_trial_count(ledger)
    expected_trial_count = campaign_run.candidate_count * campaign_run.stratum_count
    selection_id: str | None = None
    survivor_candidate_ids: tuple[str, ...] = ()

    if (
        campaign_run.report.complete_candidate_count == campaign_run.candidate_count
        and terminal_trial_count == expected_trial_count
    ):
        survivor_candidate_ids = select_d0_pilot_survivors(
            campaign_run,
            minimum_total_trades=authorization.minimum_total_trades,
            maximum_survivors=authorization.maximum_survivors,
        )
        selection_definition = {
            "authorization_schema": AUTHORIZATION_SCHEMA,
            "authorization_request_id": authorization.request_id,
            "selection_policy": dict(authorization.selection_policy),
            "stage": "D0_DISCOVERY_ONLY",
            "fresh_confirmation_evidence": False,
            "verification_authority": False,
            "d1_opened": False,
            "frozen_oos_opened": False,
            "live_execution_allowed": False,
        }
        selection_id = freeze_d0_pilot_survivors(
            ledger=ledger,
            campaign_run=campaign_run,
            candidate_ids=survivor_candidate_ids,
            selection_definition=selection_definition,
        )

    status_payload = _build_status_payload(
        authorization=authorization,
        campaign_run=campaign_run,
        terminal_trial_count=terminal_trial_count,
        selection_id=selection_id,
        survivor_candidate_ids=survivor_candidate_ids,
    )
    write_sfv2_d0_status(status_payload, path=status_path)
    return AuthorizedD0CycleResult(
        phase=str(status_payload["phase"]),
        campaign_run=campaign_run,
        terminal_trial_count=terminal_trial_count,
        expected_trial_count=expected_trial_count,
        selection_id=selection_id,
        survivor_candidate_ids=survivor_candidate_ids,
        status_payload=status_payload,
    )
