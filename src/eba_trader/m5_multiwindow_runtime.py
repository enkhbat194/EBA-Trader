from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT
from .m5_multiwindow import (
    REPORT_SCHEMA,
    M5MultiWindowCandidate,
    M5MultiWindowConfig,
    evaluate_m5_multiwindow,
    load_m5_multiwindow_candidates,
    write_immutable_m5_multiwindow_report,
)
from .m5_study_policy import DEFAULT_M5_DEVELOPMENT_CORPUS
from .research_evidence import canonical_json, sha256_text

STATUS_SCHEMA = "m5_multiwindow_runtime_status_v1"
CORPUS_STATUS_SCHEMA = "m5_corpus_runtime_status_v1"
DEFAULT_STATUS_PATH = DEFAULT_RESEARCH_ROOT / "m5-multiwindow-evaluation-latest.json"
DEFAULT_REPO_ROOT = Path("/opt/Eba-Trader")
DEFAULT_CANDIDATE_PATH = Path("config/m5_multiwindow_candidate_set_v1.json")


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


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _candidate_set_sha(candidates: tuple[M5MultiWindowCandidate, ...]) -> str:
    identity = [candidate.as_dict() for candidate in candidates]
    return sha256_text(canonical_json(identity))


def _base_status(*, phase: str, status_path: Path) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "phase": phase,
        "updatedAt": _utc_now(),
        "statusPath": str(status_path),
        "complete": False,
        "safe": True,
        "windowCount": None,
        "expectedWindowCount": len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows),
        "candidateCount": None,
        "rankingIsDevelopmentOnly": True,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }


def _load_complete_corpus_status(research_root: Path) -> dict[str, Any]:
    path = research_root / "m5-corpus-materialization-latest.json"
    payload = _read_json(path, label="M5 corpus runtime status")
    if payload.get("schema") != CORPUS_STATUS_SCHEMA:
        raise RuntimeError("M5 corpus runtime status schema mismatch")
    expected_windows = len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows)
    checks = {
        "phase": payload.get("phase") == "COMPLETE",
        "complete": payload.get("complete") is True,
        "safe": payload.get("safe") is True,
        "integrity": payload.get("integrityVerified") is True,
        "window_count": payload.get("windowCount") == expected_windows,
        "expected_count": payload.get("expectedWindowCount") == expected_windows,
        "archive": payload.get("orderflowSource") == "archive",
        "hashes": payload.get("allFeatureHashesPresent") is True,
        "legacy_oos": payload.get("frozenOosOpened") is False,
        "m5_oos": payload.get("m5FrozenOosOpened") is False,
        "live": payload.get("liveExecutionAllowed") is False,
        "edge": payload.get("edgeClaimAllowed") is False,
        "promotion": payload.get("promotionAuthority") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"M5 corpus is not ready for multi-window evaluation: {', '.join(failed)}")
    manifest_path = payload.get("manifestPath")
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        raise RuntimeError("M5 corpus runtime status is missing manifestPath")
    if not Path(manifest_path).is_file():
        raise RuntimeError("M5 corpus materialization manifest is missing")
    return payload


def _load_reusable_status(
    *,
    status_path: Path,
    materialization_id: str,
    candidate_set_sha: str,
    candidate_count: int,
) -> dict[str, Any] | None:
    if not status_path.is_file():
        return None
    payload = _read_json(status_path, label="M5 multi-window runtime status")
    expected_windows = len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows)
    if payload.get("schema") != STATUS_SCHEMA or payload.get("phase") != "COMPLETE":
        return None
    checks = (
        payload.get("complete") is True,
        payload.get("safe") is True,
        payload.get("materializationId") == materialization_id,
        payload.get("candidateSetSha256") == candidate_set_sha,
        payload.get("candidateCount") == candidate_count,
        payload.get("windowCount") == expected_windows,
        payload.get("expectedWindowCount") == expected_windows,
        payload.get("rankingIsDevelopmentOnly") is True,
        payload.get("edgeClaimAllowed") is False,
        payload.get("promotionAuthority") is False,
        payload.get("frozenOosOpened") is False,
        payload.get("m5FrozenOosOpened") is False,
        payload.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
        return None
    report_path = payload.get("reportPath")
    if not isinstance(report_path, str) or not Path(report_path).is_file():
        return None
    report = _read_json(Path(report_path), label="M5 multi-window report")
    report_checks = (
        report.get("schema") == REPORT_SCHEMA,
        report.get("evaluationId") == payload.get("evaluationId"),
        report.get("materializationId") == materialization_id,
        report.get("candidateSetSha256") == candidate_set_sha,
        report.get("candidateCount") == candidate_count,
        report.get("windowCount") == expected_windows,
        report.get("rankingIsDevelopmentOnly") is True,
        report.get("edgeClaimAllowed") is False,
        report.get("promotionAuthority") is False,
        report.get("frozenOosOpened") is False,
        report.get("m5FrozenOosOpened") is False,
        report.get("liveExecutionAllowed") is False,
    )
    return payload if all(report_checks) else None


def run_m5_multiwindow_evaluation(
    *,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    repo_root: Path = DEFAULT_REPO_ROOT,
    status_path: Path | None = None,
) -> dict[str, Any]:
    research_root = research_root.resolve()
    repo_root = repo_root.resolve()
    status_path = (status_path or (research_root / DEFAULT_STATUS_PATH.name)).resolve()
    dataset_root = (research_root / "datasets").resolve()
    evidence_root = (research_root / "evidence").resolve()
    candidates_path = repo_root / DEFAULT_CANDIDATE_PATH

    try:
        corpus = _load_complete_corpus_status(research_root)
        candidates = load_m5_multiwindow_candidates(candidates_path)
        candidate_set_sha = _candidate_set_sha(candidates)
        materialization_id = str(corpus.get("materializationId") or "")
        if not materialization_id:
            raise RuntimeError("M5 corpus runtime status is missing materializationId")

        reusable = _load_reusable_status(
            status_path=status_path,
            materialization_id=materialization_id,
            candidate_set_sha=candidate_set_sha,
            candidate_count=len(candidates),
        )
        if reusable is not None:
            return reusable

        running = {
            **_base_status(phase="RUNNING", status_path=status_path),
            "materializationId": materialization_id,
            "candidateSetSha256": candidate_set_sha,
            "candidateCount": len(candidates),
        }
        _atomic_write(status_path, running)

        report = evaluate_m5_multiwindow(
            materialization_manifest=str(corpus["manifestPath"]),
            dataset_root=dataset_root,
            candidates=candidates,
            config=M5MultiWindowConfig(),
        )
        evaluation_id = str(report["evaluationId"])
        report_path = evidence_root / f"m5-multiwindow-development-{evaluation_id}.json"
        write_immutable_m5_multiwindow_report(report_path, report)
        ranking = report.get("developmentRanking")
        if not isinstance(ranking, list) or not ranking or not isinstance(ranking[0], dict):
            raise RuntimeError("M5 multi-window report has no development ranking")
        top = ranking[0]
        baseline = report.get("baseline")
        baseline_aggregate = baseline.get("aggregate") if isinstance(baseline, dict) else None
        top_aggregate = top.get("aggregate")
        if not isinstance(baseline_aggregate, dict) or not isinstance(top_aggregate, dict):
            raise RuntimeError("M5 multi-window report aggregate metrics are missing")

        complete = {
            **_base_status(phase="COMPLETE", status_path=status_path),
            "materializationId": materialization_id,
            "policyId": report["policyId"],
            "corpusId": report["corpusId"],
            "evaluationId": evaluation_id,
            "reportPath": str(report_path),
            "candidateSetSha256": candidate_set_sha,
            "complete": True,
            "windowCount": report["windowCount"],
            "candidateCount": report["candidateCount"],
            "topDevelopmentCandidate": top.get("candidateId"),
            "topDevelopmentParameters": top.get("parameters"),
            "topDevelopmentAggregate": top_aggregate,
            "baselineAggregate": baseline_aggregate,
        }
        _atomic_write(status_path, complete)
        return complete
    except Exception as exc:
        failed = {
            **_base_status(phase="FAILED", status_path=status_path),
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:240],
        }
        _atomic_write(status_path, failed)
        raise


def main() -> int:
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    repo_root = Path(os.environ.get("EBA_REPO_DIR", str(DEFAULT_REPO_ROOT)))
    status_path = Path(
        os.environ.get(
            "EBA_M5_MULTIWINDOW_STATUS",
            str(research_root / DEFAULT_STATUS_PATH.name),
        )
    )
    try:
        payload = run_m5_multiwindow_evaluation(
            research_root=research_root,
            repo_root=repo_root,
            status_path=status_path,
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
