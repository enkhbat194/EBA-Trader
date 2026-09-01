from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .provenance import collect_source_provenance
from .research_store import ResearchStore
from .strategy_discovery_v2 import (
    MAX_CANDIDATES_PER_FAMILY,
    MAX_RAW_CANDIDATES,
    MAX_SURVIVORS,
    DiscoveryCampaignPolicy,
    DiscoveryTrialLedger,
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
