from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .binance_demo_execution import (
    CONFIG_SCHEMA,
    DemoExecutionConfig,
    run_demo_execution_probe,
)
from .credential_vault import DemoCredentialVault
from .m5_corpus_materializer import DEFAULT_RESEARCH_ROOT

DEFAULT_REPO_ROOT = Path("/opt/Eba-Trader")
DEFAULT_CONFIG_PATH = Path("config/binance_demo_execution_probe_v1.json")
DEFAULT_ROBUSTNESS_STATUS = DEFAULT_RESEARCH_ROOT / "m5-absorption-robustness-latest.json"
DEFAULT_PROOF_PATH = DEFAULT_RESEARCH_ROOT / "binance-demo-execution-latest.json"
ROBUSTNESS_STATUS_SCHEMA = "m5_absorption_robustness_runtime_status_v1"
_TERMINAL_PROOF_PHASES = {"COMPLETE", "FAILED", "BLOCKED_REVIEW", "DISABLED"}


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


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


def load_demo_execution_config(path: Path) -> DemoExecutionConfig | None:
    payload = _read_json(path, label="Binance Demo execution probe config")
    expected = {
        "schema",
        "enabled",
        "probe_id",
        "symbol",
        "target_notional_usdt",
        "max_notional_usdt",
    }
    if set(payload) != expected or payload.get("schema") != CONFIG_SCHEMA:
        raise RuntimeError("Binance Demo execution probe config schema/fields are invalid")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise RuntimeError("Binance Demo execution probe enabled must be boolean")
    if not enabled:
        return None
    config = DemoExecutionConfig(
        probe_id=str(payload.get("probe_id") or ""),
        symbol=str(payload.get("symbol") or ""),
        target_notional_usdt=float(payload.get("target_notional_usdt")),
        max_notional_usdt=float(payload.get("max_notional_usdt")),
    )
    config.validate()
    return config


def _load_completed_robustness(path: Path) -> dict[str, Any]:
    payload = _read_json(path, label="M5 robustness runtime status")
    checks = (
        payload.get("schema") == ROBUSTNESS_STATUS_SCHEMA,
        payload.get("phase") == "COMPLETE",
        payload.get("complete") is True,
        payload.get("safe") is True,
        payload.get("candidateId") == "absorption_020",
        payload.get("scenarioCount") == 9,
        payload.get("developmentEvidenceOnly") is True,
        payload.get("edgeClaimAllowed") is False,
        payload.get("promotionAuthority") is False,
        payload.get("frozenOosOpened") is False,
        payload.get("m5FrozenOosOpened") is False,
        payload.get("liveExecutionAllowed") is False,
    )
    if not all(checks):
        raise RuntimeError("M5 robustness evaluation is not safely complete")
    return payload


def _base_proof(config: DemoExecutionConfig, *, phase: str) -> dict[str, Any]:
    return {
        "schema": "binance_demo_execution_runtime_status_v1",
        "probeId": config.probe_id,
        "phase": phase,
        "passed": False,
        "updatedAt": _utc_now(),
        "environment": "demo",
        "venue": "Binance USD-M Futures Demo",
        "endpointHost": "demo-fapi.binance.com",
        "symbol": config.symbol,
        "targetNotionalUsdt": config.target_notional_usdt,
        "maxNotionalUsdt": config.max_notional_usdt,
        "orderSubmissionAttempted": False,
        "retryAutomatically": False,
        "realMoneyUsed": False,
        "liveExecutionAllowed": False,
    }


def _reuse_or_block_existing(
    *,
    proof_path: Path,
    config: DemoExecutionConfig,
) -> dict[str, Any] | None:
    if not proof_path.is_file():
        return None
    existing = _read_json(proof_path, label="Binance Demo execution proof")
    if existing.get("probeId") != config.probe_id:
        return None
    phase = str(existing.get("phase") or "UNKNOWN").upper()
    if phase in _TERMINAL_PROOF_PHASES:
        return existing
    blocked = {
        **_base_proof(config, phase="BLOCKED_REVIEW"),
        "reason": "previous one-shot probe was interrupted; automatic replay is forbidden",
        "previousPhase": phase,
        "orderSubmissionAttempted": existing.get("orderSubmissionAttempted") is True,
        "positionMayRemainOpen": True,
    }
    _atomic_write(proof_path, blocked)
    return blocked


def _preserve_terminal_proof_when_disabled(proof_path: Path) -> dict[str, Any] | None:
    if not proof_path.is_file():
        return None
    existing = _read_json(proof_path, label="Binance Demo execution proof")
    phase = str(existing.get("phase") or "UNKNOWN").upper()
    if phase not in _TERMINAL_PROOF_PHASES:
        return None
    if existing.get("environment") != "demo":
        raise RuntimeError("disabled Binance Demo probe found non-demo terminal proof")
    if existing.get("liveExecutionAllowed") is not False:
        raise RuntimeError("disabled Binance Demo probe found terminal proof with live authority")
    return existing


def run_demo_execution_runtime(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    research_root: Path = DEFAULT_RESEARCH_ROOT,
    config_path: Path | None = None,
    robustness_path: Path | None = None,
    proof_path: Path | None = None,
    vault: DemoCredentialVault | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    research_root = research_root.resolve()
    chosen_config = (config_path or (repo_root / DEFAULT_CONFIG_PATH)).resolve()
    chosen_robustness = (
        robustness_path or (research_root / DEFAULT_ROBUSTNESS_STATUS.name)
    ).resolve()
    chosen_proof = (proof_path or (research_root / DEFAULT_PROOF_PATH.name)).resolve()

    config = load_demo_execution_config(chosen_config)
    if config is None:
        preserved = _preserve_terminal_proof_when_disabled(chosen_proof)
        if preserved is not None:
            return preserved
        disabled = {
            "schema": "binance_demo_execution_runtime_status_v1",
            "phase": "DISABLED",
            "passed": False,
            "updatedAt": _utc_now(),
            "environment": "demo",
            "retryAutomatically": False,
            "realMoneyUsed": False,
            "liveExecutionAllowed": False,
        }
        _atomic_write(chosen_proof, disabled)
        return disabled

    existing = _reuse_or_block_existing(proof_path=chosen_proof, config=config)
    if existing is not None:
        return existing

    robustness = _load_completed_robustness(chosen_robustness)
    running = {
        **_base_proof(config, phase="RUNNING"),
        "robustnessId": robustness.get("robustnessId"),
        "robustnessVerified": robustness.get("robustnessVerified") is True,
        "note": "execution plumbing proof is independent of strategy profitability",
    }
    _atomic_write(chosen_proof, running)

    credential_vault = vault or DemoCredentialVault()
    credentials = credential_vault.load()
    if credentials is None:
        failed = {
            **_base_proof(config, phase="FAILED"),
            "robustnessId": robustness.get("robustnessId"),
            "errorType": "CredentialVaultError",
            "errorSummary": "encrypted Binance Demo credentials are not configured",
        }
        _atomic_write(chosen_proof, failed)
        return failed

    result = run_demo_execution_probe(credentials=credentials, config=config)
    terminal = {
        **result,
        "schema": "binance_demo_execution_runtime_status_v1",
        "updatedAt": _utc_now(),
        "robustnessId": robustness.get("robustnessId"),
        "robustnessVerified": robustness.get("robustnessVerified") is True,
        "strategyPromotionAuthority": False,
        "retryAutomatically": False,
        "realMoneyUsed": False,
        "liveExecutionAllowed": False,
    }
    _atomic_write(chosen_proof, terminal)
    return terminal


def main() -> int:
    repo_root = Path(os.environ.get("EBA_REPO_DIR", str(DEFAULT_REPO_ROOT)))
    research_root = Path(os.environ.get("EBA_RESEARCH_ROOT", str(DEFAULT_RESEARCH_ROOT)))
    proof_path = Path(
        os.environ.get(
            "EBA_DEMO_EXECUTION_PROOF_FILE",
            str(research_root / DEFAULT_PROOF_PATH.name),
        )
    )
    try:
        payload = run_demo_execution_runtime(
            repo_root=repo_root,
            research_root=research_root,
            proof_path=proof_path,
        )
    except Exception as exc:
        payload = {
            "schema": "binance_demo_execution_runtime_status_v1",
            "phase": "FAILED",
            "passed": False,
            "updatedAt": _utc_now(),
            "environment": "demo",
            "errorType": type(exc).__name__,
            "errorSummary": str(exc)[:320],
            "retryAutomatically": False,
            "realMoneyUsed": False,
            "liveExecutionAllowed": False,
        }
        _atomic_write(proof_path, payload)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    # Demo execution is an observational proof. A failed proof must not break research
    # maintenance or trigger repeated exchange orders through service retries.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
