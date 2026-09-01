from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .research_evidence import canonical_json, sha256_file, sha256_text
from .research_store import ResearchStore
from .strategy_discovery_v2 import (
    DISCOVERY_AUTHORITY,
    MAX_CANDIDATES_PER_FAMILY,
    MAX_RAW_CANDIDATES,
    MAX_SURVIVORS,
    DiscoveryCampaignPolicy,
    DiscoveryTrialLedger,
)
from .strategy_factory_v2_catalog import (
    PILOT_SEED,
    generate_pilot_candidates,
    planned_raw_candidate_count,
)
from .strategy_factory_v2_d0 import D0_PROVENANCE_CLASS
from .strategy_factory_v2_d0_existing import load_existing_d0_from_inspected_m5
from .strategy_factory_v2_pilot import (
    DEFAULT_WARMUP_BARS,
    build_low_fidelity_report,
    materialize_low_fidelity_strata,
    run_low_fidelity_stratum,
)

STATUS_SCHEMA = "strategy_factory_v2_d0_pilot_runtime_v1"
REPORT_SCHEMA = "strategy_factory_v2_d0_low_fidelity_report_v1"
CAMPAIGN_ID = "sfv2-d0-pilot-v1"
BEHAVIORAL_SIMILARITY_THRESHOLD = 0.90
DEFAULT_MAX_NEW_TRIALS = 1024
DEFAULT_MAX_COMPUTE_MS = 60_000
DEFAULT_REPO_ROOT = Path("/opt/Eba-Trader")
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "strategy-factory-v2-d0-pilot-latest.json"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TERMINAL = frozenset({"evaluated", "rejected"})


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(serialized)
        temporary = Path(handle.name)
    temporary.chmod(0o640)
    temporary.replace(path)


def _write_immutable(path: Path, payload: dict[str, Any]) -> None:
    serialized = canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != serialized:
            raise RuntimeError("immutable D0 low-fidelity report collision")
        return
    path.write_text(serialized, encoding="utf-8")
    path.chmod(0o640)


def _git_source_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    value = result.stdout.strip().lower()
    if not _GIT_SHA_RE.fullmatch(value):
        raise RuntimeError("Strategy Factory v2 runtime requires an exact Git commit SHA")
    return value


def _candidate_set_sha(candidates: tuple[Any, ...]) -> str:
    return sha256_text(canonical_json([candidate.specification for candidate in candidates]))


def _base_status(*, phase: str, status_path: Path) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": phase,
        "updatedAt": _utc_now(),
        "statusPath": str(status_path),
        "campaignId": CAMPAIGN_ID,
        "complete": False,
        "safe": True,
        "authority": DISCOVERY_AUTHORITY,
        "provenanceClass": D0_PROVENANCE_CLASS,
        "plannedCandidateCount": planned_raw_candidate_count(),
        "rawCandidateCap": MAX_RAW_CANDIDATES,
        "perFamilyCap": MAX_CANDIDATES_PER_FAMILY,
        "survivorCap": MAX_SURVIVORS,
        "behavioralSimilarityThreshold": BEHAVIORAL_SIMILARITY_THRESHOLD,
        "warmupBarsRequested": DEFAULT_WARMUP_BARS,
        "selectionOnly": True,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "survivorSelectionFrozen": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _safe_report_candidate(item: Any) -> dict[str, Any]:
    payload = asdict(item)
    behavior = item.behavior.as_dict() if item.behavior is not None else None
    payload["behavior"] = behavior
    return payload


def _trial_counts(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "trialCount": len(trials),
        "terminalTrialCount": sum(str(row.get("status")) in _TERMINAL for row in trials),
        "evaluatedTrialCount": sum(row.get("status") == "evaluated" for row in trials),
        "rejectedTrialCount": sum(row.get("status") == "rejected" for row in trials),
        "declaredTrialCount": sum(row.get("status") == "declared" for row in trials),
    }


def _expected_trial_identity(strata: tuple[Any, ...], candidates: tuple[Any, ...]) -> set[tuple[str, str, str]]:
    return {
        (candidate.candidate_id, stratum.fidelity, stratum.dataset_sha256)
        for stratum in strata
        for candidate in candidates
    }


def _ledger_complete(
    *,
    ledger: DiscoveryTrialLedger,
    candidates: tuple[Any, ...],
    strata: tuple[Any, ...],
) -> bool:
    candidate_rows = ledger.list_candidates(CAMPAIGN_ID)
    trials = ledger.list_trials(CAMPAIGN_ID)
    if len(candidate_rows) != len(candidates):
        return False
    expected = _expected_trial_identity(strata, candidates)
    observed = {
        (str(row["candidate_id"]), str(row["fidelity"]), str(row["dataset_sha256"]))
        for row in trials
        if str(row.get("status")) in _TERMINAL
    }
    return observed == expected and len(trials) == len(expected)


def _load_reusable_complete_status(
    *,
    status_path: Path,
    evidence_root: Path,
    declaration_sha: str,
    dataset_sha: str,
    candidate_set_sha: str,
    ledger: DiscoveryTrialLedger,
    candidates: tuple[Any, ...],
    strata: tuple[Any, ...],
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    checks = (
        isinstance(payload, dict),
        payload.get("schema") == STATUS_SCHEMA if isinstance(payload, dict) else False,
        payload.get("phase") == "COMPLETE" if isinstance(payload, dict) else False,
        payload.get("complete") is True if isinstance(payload, dict) else False,
        payload.get("safe") is True if isinstance(payload, dict) else False,
        payload.get("authority") == DISCOVERY_AUTHORITY if isinstance(payload, dict) else False,
        payload.get("provenanceClass") == D0_PROVENANCE_CLASS if isinstance(payload, dict) else False,
        payload.get("sourceDeclarationSha256") == declaration_sha if isinstance(payload, dict) else False,
        payload.get("datasetSha256") == dataset_sha if isinstance(payload, dict) else False,
        payload.get("candidateSetSha256") == candidate_set_sha if isinstance(payload, dict) else False,
        payload.get("freshConfirmationEvidence") is False if isinstance(payload, dict) else False,
        payload.get("verificationAuthority") is False if isinstance(payload, dict) else False,
        payload.get("survivorSelectionFrozen") is False if isinstance(payload, dict) else False,
        payload.get("d1Opened") is False if isinstance(payload, dict) else False,
        payload.get("frozenOosOpened") is False if isinstance(payload, dict) else False,
        payload.get("liveExecutionAllowed") is False if isinstance(payload, dict) else False,
    )
    if not all(checks) or not _ledger_complete(ledger=ledger, candidates=candidates, strata=strata):
        return None
    report_path_raw = payload.get("reportPath")
    report_sha = payload.get("reportSha256")
    if not isinstance(report_path_raw, str) or not isinstance(report_sha, str):
        return None
    try:
        report_path = Path(report_path_raw).resolve()
        report_path.relative_to(evidence_root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    if not report_path.is_file() or sha256_file(report_path) != report_sha:
        return None
    return payload


def _build_complete_report(
    *,
    declaration: Any,
    source_code_sha: str,
    candidate_set_sha: str,
    candidates: tuple[Any, ...],
    strata: tuple[Any, ...],
    trials: list[dict[str, Any]],
) -> tuple[dict[str, Any], Any]:
    expected_strata = tuple(item.stratum.stratum_id for item in strata)
    report = build_low_fidelity_report(
        trials=trials,
        expected_strata=expected_strata,
        behavioral_similarity_threshold=BEHAVIORAL_SIMILARITY_THRESHOLD,
    )
    if report.complete_candidate_count != len(candidates):
        raise RuntimeError("D0 low-fidelity report built before all candidates were complete")
    payload = {
        "schema": REPORT_SCHEMA,
        "authority": DISCOVERY_AUTHORITY,
        "provenanceClass": D0_PROVENANCE_CLASS,
        "campaignId": CAMPAIGN_ID,
        "sourceDeclarationSha256": declaration.declaration_sha256,
        "datasetSha256": declaration.manifest.dataset_sha256,
        "sourceCodeSha": source_code_sha,
        "candidateSeed": PILOT_SEED,
        "candidateSetSha256": candidate_set_sha,
        "plannedCandidateCount": len(candidates),
        "expectedTrialCount": len(candidates) * len(strata),
        "expectedStrata": list(expected_strata),
        "behavioralSimilarityThreshold": BEHAVIORAL_SIMILARITY_THRESHOLD,
        "completeCandidateCount": report.complete_candidate_count,
        "rejectedCandidateCount": report.rejected_candidate_count,
        "behavioralRepresentativeCount": len(report.representative_candidate_ids),
        "representativeCandidateIds": list(report.representative_candidate_ids),
        "candidates": [_safe_report_candidate(item) for item in report.candidates],
        "selectionOnly": True,
        "freshConfirmationEvidence": False,
        "verificationAuthority": False,
        "survivorSelectionFrozen": False,
        "d1Opened": False,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    return payload, report


def run_d0_pilot(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    repo_root: Path = DEFAULT_REPO_ROOT,
    status_path: Path | None = None,
    max_new_trials: int = DEFAULT_MAX_NEW_TRIALS,
    max_compute_ms: int = DEFAULT_MAX_COMPUTE_MS,
    source_code_sha: str | None = None,
) -> dict[str, Any]:
    if max_new_trials <= 0:
        raise ValueError("max_new_trials must be positive")
    if max_compute_ms <= 0:
        raise ValueError("max_compute_ms must be positive")

    research_root = research_root.resolve()
    repo_root = repo_root.resolve()
    chosen_status = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    dataset_root = (research_root / "datasets").resolve()
    evidence_root = (research_root / "evidence").resolve()
    database_path = (research_root / "eba_research.db").resolve()
    exact_code_sha = (source_code_sha or _git_source_sha(repo_root)).strip().lower()
    if not _GIT_SHA_RE.fullmatch(exact_code_sha):
        raise ValueError("source_code_sha must be an exact 40-character Git SHA")

    try:
        declaration, rows, materialization = load_existing_d0_from_inspected_m5(
            dataset_root=dataset_root
        )
        if declaration.authority != DISCOVERY_AUTHORITY:
            raise RuntimeError("D0 pilot source authority changed")
        if declaration.provenance_class != D0_PROVENANCE_CLASS:
            raise RuntimeError("D0 pilot source provenance changed")
        candles = tuple(row.candle for row in rows)
        strata = materialize_low_fidelity_strata(
            manifest=declaration.manifest,
            candles=candles,
            orderflow_rows=rows,
            warmup_bars=DEFAULT_WARMUP_BARS,
        )
        if len(strata) != len(materialization.windows) or len(strata) != 12:
            raise RuntimeError("D0 pilot requires the 12 declared inspected source windows")

        candidates = generate_pilot_candidates(seed=PILOT_SEED)
        if len(candidates) != planned_raw_candidate_count() or len(candidates) != 406:
            raise RuntimeError("D0 pilot candidate catalog changed from the declared 406 candidates")
        candidate_sha = _candidate_set_sha(candidates)

        store = ResearchStore(database_path)
        ledger = DiscoveryTrialLedger(store)
        reusable = _load_reusable_complete_status(
            status_path=chosen_status,
            evidence_root=evidence_root,
            declaration_sha=declaration.declaration_sha256,
            dataset_sha=declaration.manifest.dataset_sha256,
            candidate_set_sha=candidate_sha,
            ledger=ledger,
            candidates=candidates,
            strata=strata,
        )
        if reusable is not None:
            return reusable

        running = {
            **_base_status(phase="RUNNING", status_path=chosen_status),
            "sourceKind": declaration.source_kind,
            "materializationId": declaration.source_materialization_id,
            "sourceDeclarationSha256": declaration.declaration_sha256,
            "datasetSha256": declaration.manifest.dataset_sha256,
            "sourceCodeSha": exact_code_sha,
            "candidateSeed": PILOT_SEED,
            "candidateSetSha256": candidate_sha,
            "expectedStratumCount": len(strata),
            "expectedTrialCount": len(candidates) * len(strata),
            "maxNewTrialsPerRun": max_new_trials,
            "maxComputeMsPerRun": max_compute_ms,
        }
        _atomic_write(chosen_status, running)

        policy = DiscoveryCampaignPolicy(campaign_id=CAMPAIGN_ID)
        ledger.register_campaign(
            policy,
            definition={
                "schema": STATUS_SCHEMA,
                "authority": DISCOVERY_AUTHORITY,
                "provenance_class": D0_PROVENANCE_CLASS,
                "source_declaration_sha256": declaration.declaration_sha256,
                "dataset_sha256": declaration.manifest.dataset_sha256,
                "source_code_sha": exact_code_sha,
                "candidate_seed": PILOT_SEED,
                "candidate_set_sha256": candidate_sha,
                "planned_candidate_count": len(candidates),
                "expected_strata": [item.stratum.stratum_id for item in strata],
                "behavioral_similarity_threshold": BEHAVIORAL_SIMILARITY_THRESHOLD,
                "warmup_bars_requested": DEFAULT_WARMUP_BARS,
                "fresh_confirmation_evidence": False,
                "verification_authority": False,
                "d1_opened": False,
                "frozen_oos_opened": False,
                "live_execution_allowed": False,
            },
        )

        trials = ledger.list_trials(CAMPAIGN_ID)
        terminal = {
            (str(row["candidate_id"]), str(row["fidelity"]))
            for row in trials
            if str(row.get("status")) in _TERMINAL
        }
        remaining_trials = max_new_trials
        remaining_compute = max_compute_ms
        new_trial_count = 0
        new_compute_ms = 0

        for stratum in strata:
            if remaining_trials <= 0 or remaining_compute <= 0:
                break
            pending = tuple(
                candidate
                for candidate in candidates
                if (candidate.candidate_id, stratum.fidelity) not in terminal
            )
            if not pending:
                continue
            batch = pending[:remaining_trials]
            summary = run_low_fidelity_stratum(
                ledger=ledger,
                campaign_id=CAMPAIGN_ID,
                source_code_sha=exact_code_sha,
                search_round=0,
                max_compute_ms=remaining_compute,
                candidates=batch,
                stratum_dataset=stratum,
            )
            newly_terminal = len(summary.evaluated_trial_ids)
            new_trial_count += newly_terminal
            new_compute_ms += summary.total_compute_ms
            remaining_trials -= newly_terminal
            remaining_compute = max(0, remaining_compute - summary.total_compute_ms)
            terminal.update((candidate.candidate_id, stratum.fidelity) for candidate in batch[:newly_terminal])
            if summary.stopped_for_compute_budget:
                break

        trials = ledger.list_trials(CAMPAIGN_ID)
        counts = _trial_counts(trials)
        expected_trial_count = len(candidates) * len(strata)
        complete = _ledger_complete(ledger=ledger, candidates=candidates, strata=strata)

        if not complete:
            partial = {
                **running,
                **counts,
                "phase": "PARTIAL",
                "updatedAt": _utc_now(),
                "newTerminalTrialsThisRun": new_trial_count,
                "newComputeMsThisRun": new_compute_ms,
                "complete": False,
                "selectionOnlyAggregationBuilt": False,
            }
            _atomic_write(chosen_status, partial)
            return partial

        report_payload, report = _build_complete_report(
            declaration=declaration,
            source_code_sha=exact_code_sha,
            candidate_set_sha=candidate_sha,
            candidates=candidates,
            strata=strata,
            trials=trials,
        )
        report_identity = sha256_text(canonical_json(report_payload))
        report_path = evidence_root / f"strategy-factory-v2-d0-low-{report_identity[:24]}.json"
        _write_immutable(report_path, report_payload)
        report_sha = sha256_file(report_path)
        if counts["terminalTrialCount"] != expected_trial_count:
            raise RuntimeError("D0 pilot complete state has incomplete trial accounting")

        complete_status = {
            **running,
            **counts,
            "phase": "COMPLETE",
            "updatedAt": _utc_now(),
            "complete": True,
            "newTerminalTrialsThisRun": new_trial_count,
            "newComputeMsThisRun": new_compute_ms,
            "completeCandidateCount": report.complete_candidate_count,
            "rejectedCandidateCount": report.rejected_candidate_count,
            "behavioralRepresentativeCount": len(report.representative_candidate_ids),
            "selectionOnlyAggregationBuilt": True,
            "reportPath": str(report_path),
            "reportSha256": report_sha,
        }
        _atomic_write(chosen_status, complete_status)
        return complete_status
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=chosen_status),
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:240],
        }
        _atomic_write(chosen_status, failed)
        raise


def main() -> int:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    repo_root = Path(os.environ.get("EBA_REPO_DIR", str(DEFAULT_REPO_ROOT)))
    status_path = Path(
        os.environ.get(
            "EBA_SFV2_D0_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    max_new_trials = int(os.environ.get("EBA_SFV2_D0_MAX_NEW_TRIALS", DEFAULT_MAX_NEW_TRIALS))
    max_compute_ms = int(os.environ.get("EBA_SFV2_D0_MAX_COMPUTE_MS", DEFAULT_MAX_COMPUTE_MS))
    try:
        payload = run_d0_pilot(
            research_root=research_root,
            repo_root=repo_root,
            status_path=status_path,
            max_new_trials=max_new_trials,
            max_compute_ms=max_compute_ms,
        )
    except Exception:
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {"schema": STATUS_SCHEMA, "phase": "FAILED", "safe": True}
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
