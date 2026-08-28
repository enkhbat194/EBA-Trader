#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("/var/lib/eba-trader/proofs/latest.json")
JOURNALD_DROPIN = Path("/etc/systemd/journald.conf.d/eba-trader.conf")
RESEARCH_ROOT = Path("/var/lib/eba-trader/research")
RESEARCH_DATASETS = RESEARCH_ROOT / "datasets"
RESEARCH_EVIDENCE = RESEARCH_ROOT / "evidence"
RESEARCH_DB = RESEARCH_ROOT / "eba_research.db"
M5_ABLATION_PROOF = RESEARCH_ROOT / "m5-real-ablation-latest.json"
M5_CORPUS_PROOF = RESEARCH_ROOT / "m5-corpus-materialization-latest.json"
M5_MULTIWINDOW_PROOF = RESEARCH_ROOT / "m5-multiwindow-evaluation-latest.json"
EXPECTED_M5_CORPUS_WINDOWS = 12
EXPECTED_M5_MULTIWINDOW_CANDIDATES = 17
M5_MULTIWINDOW_REPORT_SCHEMA = "m5_multiwindow_development_report_v1"
RUNTIME_API = "http://127.0.0.1:8765"
WEB_API = "http://127.0.0.1:8000"


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 12.0,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not isinstance(body, dict):
        raise RuntimeError(f"non-object JSON from {url}")
    return body


def _safe_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 12.0,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _request_json(url, method=method, payload=payload, timeout=timeout), None
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        return None, str(exc)[:240]


def _unit_active(unit: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", unit],
        check=False,
        capture_output=True,
        timeout=5,
    )
    return result.returncode == 0


def _journald_contract() -> dict[str, Any]:
    expected = {
        "SystemMaxUse": "250M",
        "SystemKeepFree": "1G",
        "MaxRetentionSec": "7day",
    }
    try:
        text = JOURNALD_DROPIN.read_text(encoding="utf-8")
    except OSError as exc:
        return {"passed": False, "error": str(exc)[:240], "expected": expected}
    actual: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        actual[key.strip()] = value.strip()
    return {
        "passed": all(actual.get(key) == value for key, value in expected.items()),
        "expected": expected,
        "actual": {key: actual.get(key) for key in expected},
    }


def _research_contract() -> dict[str, Any]:
    directories = {
        "root": RESEARCH_ROOT.is_dir(),
        "datasets": RESEARCH_DATASETS.is_dir(),
        "evidence": RESEARCH_EVIDENCE.is_dir(),
    }
    return {
        "passed": all(directories.values()) and _unit_active("eba-research-worker.timer"),
        "directories": directories,
        "databaseExists": RESEARCH_DB.is_file(),
        "workerTimerActive": _unit_active("eba-research-worker.timer"),
    }


def _service_contract() -> dict[str, Any]:
    units = {
        unit: _unit_active(unit)
        for unit in (
            "eba-binance-data.service",
            "eba-runtime-api.service",
            "eba-web.service",
            "eba-auto-update.timer",
            "eba-research-worker.timer",
            "eba-m5-real-ablation.timer",
        )
    }
    return {"passed": all(units.values()), "units": units}


def _m5_ablation_status() -> dict[str, Any]:
    timer_active = _unit_active("eba-m5-real-ablation.timer")
    base: dict[str, Any] = {
        "provisioned": timer_active,
        "timerActive": timer_active,
        "available": M5_ABLATION_PROOF.is_file(),
        "phase": "WAITING",
        "safe": True,
        "frozenOosOpened": False,
        "liveExecutionAllowed": False,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
    }
    if not M5_ABLATION_PROOF.is_file():
        return base

    try:
        payload = json.loads(M5_ABLATION_PROOF.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": str(exc)[:240],
        }
    if not isinstance(payload, dict):
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": "M5 autorun marker is not a JSON object",
        }

    allowed = {
        "schema",
        "phase",
        "updatedAt",
        "windowId",
        "start",
        "end",
        "reportPath",
        "exitCode",
        "failureStage",
        "errorSummary",
        "batchId",
        "workflowId",
        "treatmentCount",
        "allTerminal",
        "allExperimentsPassed",
        "evidenceComplete",
        "edgeClaimAllowed",
        "promotionAuthority",
        "frozenOosOpened",
        "liveExecutionAllowed",
    }
    sanitized = {key: payload.get(key) for key in allowed if key in payload}
    phase = str(payload.get("phase") or "UNKNOWN").upper()
    frozen_opened = payload.get("frozenOosOpened")
    live_allowed = payload.get("liveExecutionAllowed")
    edge_allowed = payload.get("edgeClaimAllowed", False)
    promotion_authority = payload.get("promotionAuthority", False)
    locks_safe = (
        frozen_opened is False
        and live_allowed is False
        and edge_allowed is False
        and promotion_authority is False
    )
    complete_safe = True
    if phase == "COMPLETE":
        complete_safe = (
            payload.get("allTerminal") is True
            and payload.get("evidenceComplete") is True
        )
    sanitized.update(
        {
            "provisioned": timer_active,
            "timerActive": timer_active,
            "available": True,
            "phase": phase,
            "safe": bool(locks_safe and complete_safe),
            "edgeClaimAllowed": False,
            "promotionAuthority": False,
            "frozenOosOpened": frozen_opened,
            "liveExecutionAllowed": live_allowed,
        }
    )
    return sanitized


def _m5_corpus_status() -> dict[str, Any]:
    base: dict[str, Any] = {
        "available": M5_CORPUS_PROOF.is_file(),
        "phase": "WAITING",
        "complete": False,
        "safe": True,
        "integrityVerified": False,
        "expectedWindowCount": EXPECTED_M5_CORPUS_WINDOWS,
        "windowCount": None,
        "orderflowSource": "archive",
        "allFeatureHashesPresent": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
    }
    if not M5_CORPUS_PROOF.is_file():
        return base

    try:
        payload = json.loads(M5_CORPUS_PROOF.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": str(exc)[:240],
        }
    if not isinstance(payload, dict) or payload.get("schema") != "m5_corpus_runtime_status_v1":
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": "M5 corpus runtime status has an invalid schema",
        }

    allowed = {
        "schema",
        "phase",
        "updatedAt",
        "materializationId",
        "policyId",
        "corpusId",
        "manifestPath",
        "complete",
        "integrityVerified",
        "expectedWindowCount",
        "windowCount",
        "orderflowSource",
        "allFeatureHashesPresent",
        "errorType",
        "errorSummary",
        "frozenOosOpened",
        "m5FrozenOosOpened",
        "liveExecutionAllowed",
        "edgeClaimAllowed",
        "promotionAuthority",
    }
    sanitized = {key: payload.get(key) for key in allowed if key in payload}
    phase = str(payload.get("phase") or "UNKNOWN").upper()
    locks_safe = (
        payload.get("frozenOosOpened") is False
        and payload.get("m5FrozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
    )
    complete = phase == "COMPLETE"
    complete_valid = True
    if complete:
        complete_valid = (
            payload.get("complete") is True
            and payload.get("integrityVerified") is True
            and payload.get("expectedWindowCount") == EXPECTED_M5_CORPUS_WINDOWS
            and payload.get("windowCount") == EXPECTED_M5_CORPUS_WINDOWS
            and payload.get("orderflowSource") == "archive"
            and payload.get("allFeatureHashesPresent") is True
        )
    sanitized.update(
        {
            "available": True,
            "phase": phase,
            "complete": bool(complete and complete_valid),
            "safe": bool(locks_safe and complete_valid),
            "expectedWindowCount": EXPECTED_M5_CORPUS_WINDOWS,
            "edgeClaimAllowed": False,
            "promotionAuthority": False,
        }
    )
    return sanitized


def _safe_numeric_map(value: object) -> dict[str, int | float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int | float] = {}
    for raw_key, raw_value in value.items():
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            continue
        number = float(raw_value)
        if not math.isfinite(number):
            continue
        result[str(raw_key)] = raw_value
    return result


def _safe_parameters(value: object) -> dict[str, int | float]:
    allowed = {
        "delta_ratio_threshold",
        "cvd_threshold",
        "stacked_imbalance_threshold",
        "absorption_threshold",
        "exhaustion_threshold",
        "price_delta_divergence_threshold",
    }
    if not isinstance(value, dict) or not set(value) <= allowed:
        return {}
    return _safe_numeric_map(value)


def _sanitize_multiwindow_ranking(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    ranking: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            return []
        rank = item.get("developmentPriorityRank")
        candidate_id = item.get("candidateId")
        parameters = _safe_parameters(item.get("parameters"))
        aggregate = _safe_numeric_map(item.get("aggregate"))
        if (
            isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank < 1
            or not isinstance(candidate_id, str)
            or not candidate_id.strip()
            or not parameters
            or not aggregate
        ):
            return []
        ranking.append(
            {
                "developmentPriorityRank": rank,
                "candidateId": candidate_id[:96],
                "parameters": parameters,
                "aggregate": aggregate,
            }
        )
    return ranking


def _m5_multiwindow_status() -> dict[str, Any]:
    base: dict[str, Any] = {
        "available": M5_MULTIWINDOW_PROOF.is_file(),
        "phase": "WAITING",
        "complete": False,
        "safe": True,
        "expectedWindowCount": EXPECTED_M5_CORPUS_WINDOWS,
        "windowCount": None,
        "expectedCandidateCount": EXPECTED_M5_MULTIWINDOW_CANDIDATES,
        "candidateCount": None,
        "rankingIsDevelopmentOnly": True,
        "developmentRanking": [],
        "edgeClaimAllowed": False,
        "promotionAuthority": False,
        "frozenOosOpened": False,
        "m5FrozenOosOpened": False,
        "liveExecutionAllowed": False,
    }
    if not M5_MULTIWINDOW_PROOF.is_file():
        return base

    try:
        payload = json.loads(M5_MULTIWINDOW_PROOF.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": str(exc)[:240],
        }
    if not isinstance(payload, dict) or payload.get("schema") != "m5_multiwindow_runtime_status_v1":
        return {
            **base,
            "available": True,
            "phase": "INVALID",
            "safe": False,
            "error": "M5 multi-window runtime status has an invalid schema",
        }

    allowed = {
        "schema",
        "phase",
        "updatedAt",
        "materializationId",
        "policyId",
        "corpusId",
        "evaluationId",
        "reportPath",
        "candidateSetSha256",
        "complete",
        "windowCount",
        "expectedWindowCount",
        "candidateCount",
        "topDevelopmentCandidate",
        "topDevelopmentParameters",
        "topDevelopmentAggregate",
        "baselineAggregate",
        "errorType",
        "errorSummary",
        "rankingIsDevelopmentOnly",
        "edgeClaimAllowed",
        "promotionAuthority",
        "frozenOosOpened",
        "m5FrozenOosOpened",
        "liveExecutionAllowed",
    }
    sanitized = {key: payload.get(key) for key in allowed if key in payload}
    sanitized["topDevelopmentParameters"] = _safe_parameters(
        payload.get("topDevelopmentParameters")
    )
    sanitized["topDevelopmentAggregate"] = _safe_numeric_map(
        payload.get("topDevelopmentAggregate")
    )
    sanitized["baselineAggregate"] = _safe_numeric_map(payload.get("baselineAggregate"))

    phase = str(payload.get("phase") or "UNKNOWN").upper()
    locks_safe = (
        payload.get("rankingIsDevelopmentOnly") is True
        and payload.get("edgeClaimAllowed") is False
        and payload.get("promotionAuthority") is False
        and payload.get("frozenOosOpened") is False
        and payload.get("m5FrozenOosOpened") is False
        and payload.get("liveExecutionAllowed") is False
    )
    complete_valid = True
    ranking: list[dict[str, Any]] = []
    if phase == "COMPLETE":
        report_path_raw = payload.get("reportPath")
        report: dict[str, Any] | None = None
        if isinstance(report_path_raw, str) and report_path_raw.strip():
            try:
                report_path = Path(report_path_raw).resolve()
                report_path.relative_to(RESEARCH_EVIDENCE.resolve())
                report_payload = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(report_payload, dict):
                    report = report_payload
            except (OSError, ValueError, json.JSONDecodeError):
                report = None
        if report is not None:
            ranking = _sanitize_multiwindow_ranking(report.get("developmentRanking"))
        report_safe = bool(
            report is not None
            and report.get("schema") == M5_MULTIWINDOW_REPORT_SCHEMA
            and report.get("evaluationId") == payload.get("evaluationId")
            and report.get("materializationId") == payload.get("materializationId")
            and report.get("candidateSetSha256") == payload.get("candidateSetSha256")
            and report.get("windowCount") == EXPECTED_M5_CORPUS_WINDOWS
            and report.get("candidateCount") == EXPECTED_M5_MULTIWINDOW_CANDIDATES
            and report.get("rankingIsDevelopmentOnly") is True
            and report.get("edgeClaimAllowed") is False
            and report.get("promotionAuthority") is False
            and report.get("frozenOosOpened") is False
            and report.get("m5FrozenOosOpened") is False
            and report.get("liveExecutionAllowed") is False
            and len(ranking) == EXPECTED_M5_MULTIWINDOW_CANDIDATES
        )
        complete_valid = bool(
            payload.get("complete") is True
            and payload.get("expectedWindowCount") == EXPECTED_M5_CORPUS_WINDOWS
            and payload.get("windowCount") == EXPECTED_M5_CORPUS_WINDOWS
            and payload.get("candidateCount") == EXPECTED_M5_MULTIWINDOW_CANDIDATES
            and isinstance(payload.get("topDevelopmentCandidate"), str)
            and bool(sanitized["topDevelopmentAggregate"])
            and bool(sanitized["baselineAggregate"])
            and report_safe
        )

    sanitized.update(
        {
            "available": True,
            "phase": phase,
            "complete": bool(phase == "COMPLETE" and complete_valid),
            "safe": bool(locks_safe and complete_valid),
            "expectedWindowCount": EXPECTED_M5_CORPUS_WINDOWS,
            "expectedCandidateCount": EXPECTED_M5_MULTIWINDOW_CANDIDATES,
            "developmentRanking": ranking,
            "rankingIsDevelopmentOnly": True,
            "edgeClaimAllowed": False,
            "promotionAuthority": False,
        }
    )
    return sanitized


def _local_api_contract(expected_build: str | None) -> dict[str, Any]:
    health, health_error = _safe_request(f"{WEB_API}/api/health")
    runtime_health, runtime_error = _safe_request(f"{RUNTIME_API}/health")
    app_info, app_error = _safe_request(f"{WEB_API}/api/app-info")
    research, research_error = _safe_request(f"{WEB_API}/api/research/status")
    positions, positions_error = _safe_request(f"{RUNTIME_API}/api/v1/positions")

    build_sha = str((app_info or {}).get("buildSha") or "")
    build_match = True
    if expected_build:
        build_match = build_sha == expected_build or build_sha.startswith(expected_build)

    research_locks = (research or {}).get("locks")
    research_safe = isinstance(research_locks, dict) and bool(
        research_locks.get("frozenOos") and research_locks.get("realExecution")
    )
    position_rows = (positions or {}).get("positions")
    positions_ok = isinstance(position_rows, list)

    return {
        "passed": bool(
            (health or {}).get("ok")
            and (runtime_health or {}).get("ok")
            and (app_info or {}).get("ok")
            and build_match
            and (research or {}).get("ok")
            and research_safe
            and positions_ok
        ),
        "webHealth": bool((health or {}).get("ok")),
        "runtimeHealth": bool((runtime_health or {}).get("ok")),
        "appInfo": bool((app_info or {}).get("ok")),
        "buildSha": build_sha or None,
        "expectedBuild": expected_build,
        "buildMatch": build_match,
        "research": bool((research or {}).get("ok")),
        "researchLocksSafe": research_safe,
        "positions": positions_ok,
        "positionCount": len(position_rows) if isinstance(position_rows, list) else None,
        "errors": [
            item
            for item in (health_error, runtime_error, app_error, research_error, positions_error)
            if item
        ],
    }


def _demo_reconnect_contract() -> dict[str, Any]:
    status, status_error = _safe_request(f"{WEB_API}/api/demo/credential-status")
    configured = bool((status or {}).get("configured"))
    mode = str((status or {}).get("credentialMode") or "")
    result: dict[str, Any] = {
        "configured": configured,
        "credentialMode": mode or None,
        "maskedApiKey": (status or {}).get("maskedApiKey"),
        "statusError": status_error,
        "passed": False,
    }
    if not configured:
        result["state"] = "not_configured"
        return result

    reconnect, reconnect_error = _safe_request(
        f"{WEB_API}/api/demo/autoconnect",
        method="POST",
        payload={},
        timeout=20.0,
    )
    result.update(
        {
            "state": (reconnect or {}).get("state"),
            "ok": bool((reconnect or {}).get("ok")),
            "runtime": (reconnect or {}).get("runtime"),
            "liveExecutionAllowed": bool((reconnect or {}).get("liveExecutionAllowed", False)),
            "reconnectError": reconnect_error,
        }
    )
    result["passed"] = bool(
        result["ok"]
        and mode == "encrypted_server_vault"
        and result["liveExecutionAllowed"] is False
    )
    return result


def _chart_contract() -> dict[str, Any]:
    chart, error = _safe_request(
        f"{WEB_API}/api/chart",
        method="POST",
        payload={
            "provider": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "limit": 8,
        },
        timeout=20.0,
    )
    candles = (chart or {}).get("candles")
    passed = bool(
        isinstance(candles, list)
        and len(candles) >= 2
        and (chart or {}).get("provider") == "binance"
        and (chart or {}).get("symbol") == "BTCUSDT"
        and (chart or {}).get("liveExecutionAllowed") is False
    )
    return {
        "passed": passed,
        "candleCount": len(candles) if isinstance(candles, list) else 0,
        "provider": (chart or {}).get("provider"),
        "symbol": (chart or {}).get("symbol"),
        "error": error,
    }


def collect(*, expected_build: str | None = None) -> dict[str, Any]:
    proof = {
        "schemaVersion": 1,
        "collectedAt": _utc_now(),
        "journald": _journald_contract(),
        "researchRuntime": _research_contract(),
        "services": _service_contract(),
        "m5RealAblation": _m5_ablation_status(),
        "m5Corpus": _m5_corpus_status(),
        "m5MultiWindow": _m5_multiwindow_status(),
        "localApi": _local_api_contract(expected_build),
        "demoReconnect": _demo_reconnect_contract(),
        "chart": _chart_contract(),
        "safety": {
            "realExecutionAllowed": False,
            "secretPersistedInProof": False,
        },
    }
    required_local = (
        proof["journald"]["passed"],
        proof["researchRuntime"]["passed"],
        proof["services"]["passed"],
        proof["m5RealAblation"]["safe"],
        proof["m5Corpus"]["safe"],
        proof["m5MultiWindow"]["safe"],
        proof["localApi"]["passed"],
    )
    proof["localContractPassed"] = all(required_local)
    proof["productionSmokePassed"] = bool(
        proof["localContractPassed"]
        and proof["demoReconnect"]["passed"]
        and proof["chart"]["passed"]
    )
    return proof


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
        temp_path = Path(handle.name)
    temp_path.chmod(0o640)
    temp_path.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect sanitized Linode production proof")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-build", default=None)
    args = parser.parse_args()

    proof = collect(expected_build=args.expected_build)
    _atomic_write(args.output, proof)
    print(json.dumps(proof, sort_keys=True, separators=(",", ":")))
    return 0 if proof["localContractPassed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
