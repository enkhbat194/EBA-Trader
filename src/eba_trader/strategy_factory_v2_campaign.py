from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .provenance import collect_source_provenance
from .research_evidence import canonical_json, sha256_text
from .research_store import ResearchStore
from .strategy_discovery_v2 import (
    MAX_CANDIDATES_PER_FAMILY,
    MAX_RAW_CANDIDATES,
    MAX_SURVIVORS,
    DiscoveryCampaignPolicy,
    DiscoveryTrialLedger,
)
from .strategy_factory_v2_accounting import (
    LowFidelityCampaignAccounting,
    build_low_fidelity_campaign_accounting,
)
from .strategy_factory_v2_catalog import PILOT_SEED, generate_pilot_candidates
from .strategy_factory_v2_d0_existing import load_existing_d0_from_inspected_m5
from .strategy_factory_v2_d0_source import D0SourceDeclaration
from .strategy_factory_v2_pilot import (
    DEFAULT_WARMUP_BARS,
    LowFidelityDiscoveryReport,
    build_low_fidelity_report,
    materialize_low_fidelity_strata,
    run_low_fidelity_stratum,
)

PILOT_CAMPAIGN_ID = "sfv2-discovery-pilot-v1"
PILOT_AUTHORITY = "DISCOVERY_ONLY"
PILOT_SEARCH_ROUND = 0
PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD = 0.90
SURVIVOR_SELECTION_SCHEMA = "strategy_factory_v2_d0_survivor_selection_v1"


@dataclass(frozen=True, slots=True)
class D0PilotCampaignRun:
    campaign_id: str
    source_code_sha: str
    d0_declaration_sha256: str
    d0_dataset_sha256: str
    candidate_count: int
    stratum_count: int
    newly_evaluated_trial_count: int
    reused_terminal_trial_count: int
    stopped_for_compute_budget: bool
    report: LowFidelityDiscoveryReport
    accounting: LowFidelityCampaignAccounting
    authority: str = PILOT_AUTHORITY
    d1_opened: bool = False
    frozen_oos_opened: bool = False
    live_execution_allowed: bool = False


def _clean_checkout_sha(
    *,
    repo_root: str | Path | None = None,
    expected_source_code_sha: str | None = None,
) -> str:
    provenance = collect_source_provenance(cwd=repo_root, require_clean=True)
    actual_sha = str(provenance.get("git_commit", "")).strip()
    if not actual_sha:
        raise RuntimeError("source provenance is missing git_commit")
    expected_sha = (expected_source_code_sha or "").strip()
    if expected_sha and expected_sha != actual_sha:
        raise RuntimeError(
            f"source checkout mismatch: expected {expected_sha}, actual {actual_sha}"
        )
    return actual_sha


def run_d0_pilot_campaign(
    *,
    ledger: DiscoveryTrialLedger,
    declaration: D0SourceDeclaration,
    source_code_sha: str,
    rows: tuple,
    max_compute_ms_per_stratum: int,
    warmup_bars: int = DEFAULT_WARMUP_BARS,
) -> D0PilotCampaignRun:
    """Run or resume the frozen 406-candidate pilot across every declared D0 stratum.

    This function has discovery authority only. It neither opens D1 nor freezes survivors, and it
    cannot transition strategy lifecycle, Frozen OOS, demo, or live execution state. Terminal
    trials are reused by the immutable ledger, so repeated calls resume safely without re-running
    completed candidate/stratum pairs.
    """

    source_code_sha = source_code_sha.strip()
    if not source_code_sha:
        raise ValueError("source_code_sha is required")
    if max_compute_ms_per_stratum <= 0:
        raise ValueError("max_compute_ms_per_stratum must be positive")
    if declaration.authority != PILOT_AUTHORITY:
        raise ValueError("D0 campaign requires DISCOVERY_ONLY authority")

    candidates = generate_pilot_candidates(seed=PILOT_SEED)
    policy = DiscoveryCampaignPolicy(
        campaign_id=PILOT_CAMPAIGN_ID,
        raw_candidate_cap=MAX_RAW_CANDIDATES,
        candidate_cap_per_family=MAX_CANDIDATES_PER_FAMILY,
        survivor_cap=MAX_SURVIVORS,
    )
    campaign_definition = {
        "schema": "strategy_factory_v2_d0_campaign_v1",
        "authority": PILOT_AUTHORITY,
        "catalog_seed": PILOT_SEED,
        "planned_candidate_count": len(candidates),
        "d0_source_kind": declaration.source_kind,
        "d0_declaration_sha256": declaration.declaration_sha256,
        "d0_dataset_sha256": declaration.manifest.dataset_sha256,
        "d0_provenance_class": declaration.provenance_class,
        "expected_strata": [item.stratum_id for item in declaration.manifest.temporal_strata],
        "warmup_bars": warmup_bars,
        "behavioral_similarity_threshold": PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
        "search_round": PILOT_SEARCH_ROUND,
        "source_code_sha": source_code_sha,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }
    ledger.register_campaign(policy, definition=campaign_definition)

    candles = tuple(row.candle for row in rows)
    strata = materialize_low_fidelity_strata(
        manifest=declaration.manifest,
        candles=candles,
        orderflow_rows=rows,
        warmup_bars=warmup_bars,
    )

    newly_evaluated = 0
    reused_terminal = 0
    stopped = False
    for stratum_dataset in strata:
        summary = run_low_fidelity_stratum(
            ledger=ledger,
            campaign_id=PILOT_CAMPAIGN_ID,
            source_code_sha=source_code_sha,
            search_round=PILOT_SEARCH_ROUND,
            max_compute_ms=max_compute_ms_per_stratum,
            candidates=candidates,
            stratum_dataset=stratum_dataset,
        )
        newly_evaluated += len(summary.evaluated_trial_ids)
        reused_terminal += len(summary.reused_terminal_trial_ids)
        stopped = stopped or summary.stopped_for_compute_budget

    report = build_low_fidelity_report(
        trials=ledger.list_trials(PILOT_CAMPAIGN_ID),
        expected_strata=tuple(item.stratum.stratum_id for item in strata),
        behavioral_similarity_threshold=PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    accounting = build_low_fidelity_campaign_accounting(
        declared_candidates=ledger.list_candidates(PILOT_CAMPAIGN_ID),
        report=report,
        behavioral_similarity_threshold=PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    return D0PilotCampaignRun(
        campaign_id=PILOT_CAMPAIGN_ID,
        source_code_sha=source_code_sha,
        d0_declaration_sha256=declaration.declaration_sha256,
        d0_dataset_sha256=declaration.manifest.dataset_sha256,
        candidate_count=len(candidates),
        stratum_count=len(strata),
        newly_evaluated_trial_count=newly_evaluated,
        reused_terminal_trial_count=reused_terminal,
        stopped_for_compute_budget=stopped,
        report=report,
        accounting=accounting,
    )


def _registered_pilot_definition(ledger: DiscoveryTrialLedger) -> Mapping[str, object]:
    """Read the immutable registered Factory campaign definition from the ledger."""

    with ledger.store._connection() as connection:
        row = connection.execute(
            """
            SELECT authority, definition_json
            FROM discovery_campaigns_v2
            WHERE campaign_id = ?
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchone()
    if row is None:
        raise KeyError(f"unknown discovery campaign: {PILOT_CAMPAIGN_ID}")
    if str(row["authority"]) != PILOT_AUTHORITY:
        raise RuntimeError("registered Strategy Factory campaign authority drifted")
    payload = json.loads(str(row["definition_json"]))
    if not isinstance(payload, Mapping):
        raise RuntimeError("registered Strategy Factory campaign definition is invalid")
    definition = payload.get("definition")
    if not isinstance(definition, Mapping):
        raise RuntimeError("registered Strategy Factory campaign definition is missing")
    return definition


def _freeze_empty_pilot_selection(
    *,
    ledger: DiscoveryTrialLedger,
    definition: Mapping[str, object],
) -> str:
    """Persist an immutable zero-survivor D0 outcome without granting downstream authority."""

    definition_payload = {
        "authority": PILOT_AUTHORITY,
        "candidate_ids": [],
        "definition": dict(definition),
    }
    definition_json = canonical_json(definition_payload)
    definition_sha256 = sha256_text(definition_json)
    selection_id = f"dsel_{definition_sha256[:24]}"

    with ledger.store._connection() as connection:
        existing = connection.execute(
            """
            SELECT * FROM discovery_survivor_selections_v2
            WHERE campaign_id = ?
            """,
            (PILOT_CAMPAIGN_ID,),
        ).fetchone()
        if existing is not None:
            if existing["definition_sha256"] != definition_sha256:
                raise RuntimeError("discovery survivor selection is immutable")
            return str(existing["selection_id"])

        connection.execute(
            """
            INSERT INTO discovery_survivor_selections_v2(
                selection_id, campaign_id, definition_sha256,
                definition_json, candidate_ids_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                selection_id,
                PILOT_CAMPAIGN_ID,
                definition_sha256,
                definition_json,
                canonical_json([]),
            ),
        )
    return selection_id


def freeze_d0_pilot_survivors(
    *,
    ledger: DiscoveryTrialLedger,
    campaign_run: D0PilotCampaignRun,
    candidate_ids: Sequence[str],
    selection_definition: Mapping[str, object],
) -> str:
    """Freeze D0 survivor identities from immutable ledger evidence only.

    The caller-supplied run object is cross-checked against the immutable campaign registration,
    but eligibility is rebuilt from ledger candidates/trials rather than trusted from that object.
    The entire declared D0 catalog must be terminal across the exact frozen strata before any
    survivor selection can be written. A zero-survivor outcome is valid and is persisted as an
    immutable negative discovery result. This helper never opens D1, Frozen OOS or execution.
    """

    if campaign_run.campaign_id != PILOT_CAMPAIGN_ID:
        raise ValueError("survivor freeze requires the frozen Strategy Factory v2 pilot campaign")
    if campaign_run.authority != PILOT_AUTHORITY:
        raise ValueError("survivor freeze must remain DISCOVERY_ONLY")
    if (
        campaign_run.d1_opened
        or campaign_run.frozen_oos_opened
        or campaign_run.live_execution_allowed
    ):
        raise RuntimeError("survivor freeze cannot run with downstream authority already open")

    selected = tuple(candidate_ids)
    if len(selected) != len(set(selected)):
        raise ValueError("survivor candidate_ids must be unique")
    if len(selected) > MAX_SURVIVORS:
        raise RuntimeError("Strategy Factory v2 survivor cap exceeded")
    if not selection_definition:
        raise ValueError("a frozen selection_definition is required")

    registered = _registered_pilot_definition(ledger)
    if registered.get("authority") != PILOT_AUTHORITY:
        raise RuntimeError("registered Strategy Factory definition must remain DISCOVERY_ONLY")
    if registered.get("source_code_sha") != campaign_run.source_code_sha:
        raise RuntimeError("survivor freeze source code does not match immutable campaign")
    if registered.get("d0_declaration_sha256") != campaign_run.d0_declaration_sha256:
        raise RuntimeError("survivor freeze D0 declaration does not match immutable campaign")
    if registered.get("d0_dataset_sha256") != campaign_run.d0_dataset_sha256:
        raise RuntimeError("survivor freeze D0 dataset does not match immutable campaign")
    if registered.get("behavioral_similarity_threshold") != PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD:
        raise RuntimeError("registered behavioral similarity threshold drifted")

    raw_expected_strata = registered.get("expected_strata")
    if not isinstance(raw_expected_strata, list):
        raise RuntimeError("registered D0 expected_strata is invalid")
    expected_strata = tuple(str(value).strip() for value in raw_expected_strata)
    if not expected_strata or any(not value for value in expected_strata):
        raise RuntimeError("registered D0 expected_strata is empty or invalid")
    if len(expected_strata) != len(set(expected_strata)):
        raise RuntimeError("registered D0 expected_strata must be unique")
    if len(expected_strata) != campaign_run.stratum_count:
        raise RuntimeError("campaign run stratum count does not match immutable campaign")

    declared_candidates = ledger.list_candidates(PILOT_CAMPAIGN_ID)
    planned_candidate_count = registered.get("planned_candidate_count")
    if not isinstance(planned_candidate_count, int) or planned_candidate_count <= 0:
        raise RuntimeError("registered planned candidate count is invalid")
    if len(declared_candidates) != planned_candidate_count:
        raise RuntimeError("survivor freeze requires the full declared candidate catalog")
    if campaign_run.candidate_count != planned_candidate_count:
        raise RuntimeError("campaign run candidate count does not match immutable campaign")
    registered_source_sha = str(registered.get("source_code_sha") or "")
    if any(
        str(row.get("source_code_sha") or "") != registered_source_sha
        for row in declared_candidates
    ):
        raise RuntimeError("declared candidate source provenance drifted")

    report = build_low_fidelity_report(
        trials=ledger.list_trials(PILOT_CAMPAIGN_ID),
        expected_strata=expected_strata,
        behavioral_similarity_threshold=PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    declared_ids = {str(row.get("candidate_id") or "") for row in declared_candidates}
    report_by_id = {item.candidate_id: item for item in report.candidates}
    if set(report_by_id) != declared_ids:
        raise RuntimeError("survivor freeze requires D0 evidence for every declared candidate")
    if any(not item.complete for item in report.candidates):
        raise RuntimeError("survivor freeze requires terminal D0 strata for the full catalog")

    accounting = build_low_fidelity_campaign_accounting(
        declared_candidates=declared_candidates,
        report=report,
        behavioral_similarity_threshold=PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    cluster_by_candidate: dict[str, str] = {}
    for cluster in accounting.clusters:
        for candidate_id in cluster.member_candidate_ids:
            if candidate_id in cluster_by_candidate:
                raise RuntimeError("behavioral cluster membership is not unique")
            cluster_by_candidate[candidate_id] = cluster.representative_candidate_id

    selected_clusters: set[str] = set()
    for candidate_id in selected:
        item = report_by_id.get(candidate_id)
        if item is None:
            raise KeyError(f"survivor candidate missing from immutable D0 evidence: {candidate_id}")
        if not item.complete or item.rejected or item.behavior is None:
            raise RuntimeError(
                "survivor candidate is not complete behaviorally eligible D0 evidence"
            )
        cluster_id = cluster_by_candidate.get(candidate_id)
        if cluster_id is None:
            raise RuntimeError("survivor candidate is missing from behavioral cluster accounting")
        if cluster_id in selected_clusters:
            raise RuntimeError(
                "survivor selection cannot take multiple candidates from one cluster"
            )
        selected_clusters.add(cluster_id)

    frozen_definition = {
        "schema": SURVIVOR_SELECTION_SCHEMA,
        "authority": PILOT_AUTHORITY,
        "source_code_sha": registered_source_sha,
        "d0_declaration_sha256": registered["d0_declaration_sha256"],
        "d0_dataset_sha256": registered["d0_dataset_sha256"],
        "expected_strata": list(expected_strata),
        "behavioral_similarity_threshold": PILOT_BEHAVIORAL_SIMILARITY_THRESHOLD,
        "selection_definition": dict(selection_definition),
        "d1_opened": False,
        "frozen_oos_opened": False,
        "live_execution_allowed": False,
    }
    if not selected:
        return _freeze_empty_pilot_selection(ledger=ledger, definition=frozen_definition)
    return ledger.freeze_survivor_selection(
        campaign_id=PILOT_CAMPAIGN_ID,
        candidate_ids=selected,
        definition=frozen_definition,
    )


def run_existing_production_d0_pilot(
    *,
    dataset_root: str | Path,
    research_db_path: str | Path,
    max_compute_ms_per_stratum: int,
    repo_root: str | Path | None = None,
    expected_source_code_sha: str | None = None,
    warmup_bars: int = DEFAULT_WARMUP_BARS,
) -> D0PilotCampaignRun:
    """Load inspected D0 and bind execution to the actual clean source checkout."""

    source_code_sha = _clean_checkout_sha(
        repo_root=repo_root,
        expected_source_code_sha=expected_source_code_sha,
    )
    declaration, rows, _ = load_existing_d0_from_inspected_m5(dataset_root=dataset_root)
    ledger = DiscoveryTrialLedger(ResearchStore(research_db_path))
    return run_d0_pilot_campaign(
        ledger=ledger,
        declaration=declaration,
        source_code_sha=source_code_sha,
        rows=rows,
        max_compute_ms_per_stratum=max_compute_ms_per_stratum,
        warmup_bars=warmup_bars,
    )
