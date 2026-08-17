from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .execution_policy import (
    EXECUTION_POLICY_NAME,
    EXECUTION_POLICY_VERSION,
    FIRST_CYCLE_ATR_MULTIPLIER,
    FIRST_CYCLE_ATR_PERIOD,
    FIRST_CYCLE_DAILY_LOSS_LIMIT,
    FIRST_CYCLE_MAX_DRAWDOWN_HALT,
    FIRST_CYCLE_RISK_FRACTION,
)
from .risk_verdict import evaluate_risk_execution_report
from .study_policy import (
    FIRST_CYCLE_FAST_EMA,
    FIRST_CYCLE_INITIAL_CASH,
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SLOW_EMA,
    FIRST_CYCLE_SYMBOL,
    FROZEN_OOS_END_EXCLUSIVE,
    FROZEN_OOS_START,
)
from .verdict import development_is_eligible


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _assert_signal_authority(
    signal_path: Path,
    signal_verdict_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    signal = _load_json(signal_path, "signal development evidence")
    verdict = _load_json(signal_verdict_path, "signal development verdict")
    if not development_is_eligible(signal):
        raise RuntimeError("Signal development evidence fails predeclared screening")
    if verdict.get("status") != "ELIGIBLE_FOR_FROZEN_OOS":
        raise RuntimeError("Signal development verdict is not eligible")
    if verdict.get("all_gates_passed") is not True:
        raise RuntimeError("Signal development verdict gates did not all pass")
    if verdict.get("development_report_sha256") != sha256_file(signal_path):
        raise RuntimeError("Signal development verdict hash does not match evidence")
    return signal, verdict


def _assert_risk_authority(
    risk_path: Path,
    risk_verdict_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    risk = _load_json(risk_path, "risk execution evidence")
    verdict = _load_json(risk_verdict_path, "risk execution verdict")
    if not all(gate.passed for gate in evaluate_risk_execution_report(risk)):
        raise RuntimeError("Risk execution evidence fails predeclared screening")
    if verdict.get("status") != "ELIGIBLE_FOR_FINAL_FROZEN_OOS":
        raise RuntimeError("Risk execution verdict is not eligible")
    if verdict.get("all_gates_passed") is not True:
        raise RuntimeError("Risk execution verdict gates did not all pass")
    if verdict.get("risk_execution_evidence_sha256") != sha256_file(risk_path):
        raise RuntimeError("Risk execution verdict hash does not match evidence")
    return risk, verdict


def _assert_dataset_hashes(risk: dict[str, object]) -> dict[str, dict[str, object]]:
    datasets = risk.get("datasets")
    if not isinstance(datasets, dict):
        raise ValueError("Risk evidence dataset provenance is missing")
    verified: dict[str, dict[str, object]] = {}
    for name in ("research", "validation"):
        item = datasets.get(name)
        if not isinstance(item, dict):
            raise ValueError(f"Risk evidence {name} dataset provenance is missing")
        path = Path(str(item.get("path", "")))
        expected_hash = str(item.get("sha256", ""))
        if not path.is_file():
            raise FileNotFoundError(f"Frozen development dataset is missing: {path}")
        actual_hash = sha256_file(path)
        if not expected_hash or actual_hash != expected_hash:
            raise RuntimeError(f"{name} development dataset changed after risk evidence")
        verified[name] = {
            "path": str(path),
            "sha256": actual_hash,
            "start": item.get("start"),
            "end_exclusive": item.get("end_exclusive"),
            "candle_count": item.get("candle_count"),
        }
    return verified


def freeze_final_oos_candidate(
    *,
    signal_path: str | Path = "artifacts/m2_development_evidence.json",
    signal_verdict_path: str | Path = "artifacts/m2_development_verdict.json",
    risk_path: str | Path = "artifacts/m2_risk_execution_evidence.json",
    risk_verdict_path: str | Path = "artifacts/m2_risk_execution_verdict.json",
    freeze_path: str | Path = "artifacts/m2_final_frozen_candidate.json",
) -> dict[str, object]:
    output = Path(freeze_path)
    if output.exists():
        raise RuntimeError("Final frozen OOS candidate already exists; overwrite is forbidden")

    signal_file = Path(signal_path)
    signal_verdict_file = Path(signal_verdict_path)
    risk_file = Path(risk_path)
    risk_verdict_file = Path(risk_verdict_path)
    signal, signal_verdict = _assert_signal_authority(signal_file, signal_verdict_file)
    risk, risk_verdict = _assert_risk_authority(risk_file, risk_verdict_file)

    signal_commit = str(signal["source_provenance"]["git_commit"])
    risk_commit = str(risk["source_provenance"]["git_commit"])
    if signal_commit != risk_commit:
        raise RuntimeError("Signal and risk execution evidence were not produced from the same Git commit")
    if risk.get("signal_development_report_sha256") != sha256_file(signal_file):
        raise RuntimeError("Risk evidence is not bound to the current signal evidence")
    if risk.get("signal_development_verdict_sha256") != sha256_file(signal_verdict_file):
        raise RuntimeError("Risk evidence is not bound to the current signal verdict")

    data_dir = Path(str(signal.get("data_dir", "")))
    if not str(data_dir):
        raise ValueError("Signal evidence data directory is missing")
    oos_cache = data_dir / f"{FIRST_CYCLE_SYMBOL.lower()}_{FIRST_CYCLE_INTERVAL}_out_of_sample.csv"
    if oos_cache.exists():
        raise RuntimeError("Frozen 2025 OOS cache already exists; final holdout is contaminated")

    datasets = _assert_dataset_hashes(risk)
    costs = risk.get("cost_scenarios")
    if not isinstance(costs, dict):
        raise ValueError("Risk evidence cost scenarios are missing")

    payload: dict[str, object] = {
        "decision": "retain_final_risk_execution_for_frozen_oos",
        "symbol": FIRST_CYCLE_SYMBOL,
        "interval": FIRST_CYCLE_INTERVAL,
        "initial_cash": FIRST_CYCLE_INITIAL_CASH,
        "strategy": {
            "fast_ema": FIRST_CYCLE_FAST_EMA,
            "slow_ema": FIRST_CYCLE_SLOW_EMA,
        },
        "execution_policy": {
            "version": EXECUTION_POLICY_VERSION,
            "name": EXECUTION_POLICY_NAME,
            "atr_period": FIRST_CYCLE_ATR_PERIOD,
            "atr_multiplier": FIRST_CYCLE_ATR_MULTIPLIER,
            "risk_fraction": FIRST_CYCLE_RISK_FRACTION,
            "daily_loss_limit": FIRST_CYCLE_DAILY_LOSS_LIMIT,
            "max_drawdown_halt": FIRST_CYCLE_MAX_DRAWDOWN_HALT,
            "spot_only": True,
            "leverage": 1.0,
            "take_profit": None,
            "normal_exit": "EMA cross-down at next bar open",
            "protective_exit": "ATR stop; adverse gaps execute at available bar open",
        },
        "cost_scenarios": costs,
        "data_dir": str(data_dir),
        "development_datasets": datasets,
        "source_git_commit": signal_commit,
        "signal_development_evidence": str(signal_file),
        "signal_development_evidence_sha256": sha256_file(signal_file),
        "signal_development_verdict": str(signal_verdict_file),
        "signal_development_verdict_sha256": sha256_file(signal_verdict_file),
        "signal_screening_status": signal_verdict["status"],
        "risk_execution_evidence": str(risk_file),
        "risk_execution_evidence_sha256": sha256_file(risk_file),
        "risk_execution_verdict": str(risk_verdict_file),
        "risk_execution_verdict_sha256": sha256_file(risk_verdict_file),
        "risk_screening_status": risk_verdict["status"],
        "oos_cache": str(oos_cache),
        "oos_cache_verified_absent_at_final_freeze": True,
        "oos_window": {
            "start": FROZEN_OOS_START,
            "end_exclusive": FROZEN_OOS_END_EXCLUSIVE,
        },
        "configuration_override_after_freeze": "forbidden",
        "retuning_after_freeze": "forbidden",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    frozen = freeze_final_oos_candidate()
    print(
        f"final_freeze={frozen['symbol']} {frozen['interval']} "
        f"EMA{frozen['strategy']['fast_ema']}/{frozen['strategy']['slow_ema']} "
        f"risk={frozen['execution_policy']['risk_fraction']:.3%}"
    )
    print(f"source_commit={frozen['source_git_commit']}")
    print("signal_screening=PASS")
    print("risk_execution_screening=PASS")
    print("oos_cache_absent=VERIFIED")
    print("configuration_override=FORBIDDEN")
    print("freeze=artifacts/m2_final_frozen_candidate.json")


if __name__ == "__main__":
    main()
