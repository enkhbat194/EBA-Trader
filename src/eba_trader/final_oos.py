from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .final_freeze import sha256_file
from .history import fetch_binance_klines, parse_utc, save_csv, validate_interval_window
from .provenance import collect_source_provenance
from .risk_evidence import risk_result_to_dict
from .risk_trend import RiskTrendConfig, run_risk_sized_trend_backtest


def _load_json(path: Path, label: str) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _verify_final_freeze(freeze_path: Path) -> dict[str, object]:
    frozen = _load_json(freeze_path, "final frozen candidate")
    if frozen.get("decision") != "retain_final_risk_execution_for_frozen_oos":
        raise ValueError("Final freeze decision is invalid")

    provenance = collect_source_provenance(require_clean=True)
    if provenance["git_commit"] != frozen.get("source_git_commit"):
        raise RuntimeError(
            "Current Git commit differs from the development/freeze commit. "
            "Do not open OOS with changed strategy code."
        )

    bindings = (
        ("signal_development_evidence", "signal_development_evidence_sha256"),
        ("signal_development_verdict", "signal_development_verdict_sha256"),
        ("risk_execution_evidence", "risk_execution_evidence_sha256"),
        ("risk_execution_verdict", "risk_execution_verdict_sha256"),
    )
    for path_key, hash_key in bindings:
        bound_path = Path(str(frozen.get(path_key, "")))
        if not bound_path.is_file():
            raise FileNotFoundError(f"Frozen authority file is missing: {bound_path}")
        if sha256_file(bound_path) != frozen.get(hash_key):
            raise RuntimeError(f"Frozen authority binding changed: {path_key}")

    datasets = frozen.get("development_datasets")
    if not isinstance(datasets, dict):
        raise ValueError("Frozen development dataset bindings are missing")
    for name in ("research", "validation"):
        item = datasets.get(name)
        if not isinstance(item, dict):
            raise ValueError(f"Frozen {name} dataset binding is missing")
        path = Path(str(item.get("path", "")))
        if not path.is_file():
            raise FileNotFoundError(f"Frozen {name} dataset is missing")
        if sha256_file(path) != item.get("sha256"):
            raise RuntimeError(f"Frozen {name} dataset changed after final freeze")

    return frozen


def _config_for_scenario(frozen: dict[str, object], scenario: dict[str, object]) -> RiskTrendConfig:
    strategy = frozen["strategy"]
    policy = frozen["execution_policy"]
    return RiskTrendConfig(
        fast_ema=int(strategy["fast_ema"]),
        slow_ema=int(strategy["slow_ema"]),
        atr_period=int(policy["atr_period"]),
        atr_multiplier=float(policy["atr_multiplier"]),
        risk_fraction=float(policy["risk_fraction"]),
        daily_loss_limit=float(policy["daily_loss_limit"]),
        max_drawdown_halt=float(policy["max_drawdown_halt"]),
        initial_cash=float(frozen["initial_cash"]),
        fee_bps=float(scenario["fee_bps"]),
        slippage_bps=float(scenario["slippage_bps"]),
    )


def run_final_oos(
    *,
    confirm_frozen: bool,
    freeze_path: str | Path = "artifacts/m2_final_frozen_candidate.json",
    opened_marker_path: str | Path = "artifacts/m2_final_oos_opened.json",
    report_path: str | Path = "artifacts/m2_final_oos_2025.json",
) -> dict[str, object]:
    if not confirm_frozen:
        raise ValueError("Final 2025 OOS is locked; explicit --confirm-frozen is required")

    freeze_file = Path(freeze_path)
    marker_file = Path(opened_marker_path)
    output = Path(report_path)
    if output.exists():
        raise RuntimeError("Final OOS report already exists; rerun is forbidden")
    if marker_file.exists():
        raise RuntimeError(
            "Final OOS was already opened or an earlier one-shot run was interrupted; "
            "do not silently rerun the holdout"
        )

    frozen = _verify_final_freeze(freeze_file)
    oos_cache = Path(str(frozen["oos_cache"]))
    if oos_cache.exists():
        raise RuntimeError("OOS cache already exists before authorized final open; holdout contaminated")

    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "status": "OPENED_PENDING_RESULT",
        "opened_at_utc": datetime.now(UTC).isoformat(),
        "final_freeze": str(freeze_file),
        "final_freeze_sha256": sha256_file(freeze_file),
        "source_git_commit": frozen["source_git_commit"],
        "rerun_policy": "forbidden",
    }
    marker_file.write_text(json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8")

    window = frozen["oos_window"]
    start_ms = parse_utc(str(window["start"]))
    end_ms = parse_utc(str(window["end_exclusive"]))
    symbol = str(frozen["symbol"])
    interval = str(frozen["interval"])

    candles = fetch_binance_klines(symbol, interval, start_ms, end_ms)
    candles = validate_interval_window(candles, interval, start_ms, end_ms)
    save_csv(candles, oos_cache)
    oos_hash = sha256_file(oos_cache)

    scenarios: dict[str, object] = {}
    costs = frozen["cost_scenarios"]
    for name in ("base", "adverse", "severe"):
        config = _config_for_scenario(frozen, costs[name])
        result = run_risk_sized_trend_backtest(candles, config)
        scenarios[name] = risk_result_to_dict(result)

    report: dict[str, object] = {
        "phase": "final_frozen_risk_execution_oos",
        "configuration_source": str(freeze_file),
        "configuration_source_sha256": sha256_file(freeze_file),
        "source_git_commit": frozen["source_git_commit"],
        "symbol": symbol,
        "interval": interval,
        "initial_cash": frozen["initial_cash"],
        "strategy": frozen["strategy"],
        "execution_policy": frozen["execution_policy"],
        "cost_scenarios": costs,
        "retuning_after_open": "forbidden",
        "rerun": "forbidden",
        "window": {
            "start": window["start"],
            "end_exclusive": window["end_exclusive"],
            "candle_count": len(candles),
            "coverage": "exact",
            "dataset_path": str(oos_cache),
            "dataset_sha256": oos_hash,
            "scenarios": scenarios,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    marker["status"] = "COMPLETE"
    marker["report"] = str(output)
    marker["report_sha256"] = sha256_file(output)
    marker["oos_dataset_sha256"] = oos_hash
    marker_file.write_text(json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open the final frozen risk-sized 2025 OOS exactly once"
    )
    parser.add_argument("--confirm-frozen", action="store_true")
    args = parser.parse_args()
    report = run_final_oos(confirm_frozen=args.confirm_frozen)
    base = report["window"]["scenarios"]["base"]
    severe = report["window"]["scenarios"]["severe"]
    print(
        f"FINAL_OOS base_return={base['total_return']:.2%} "
        f"base_dd={base['max_drawdown']:.2%} "
        f"btc={base['benchmark_return']:.2%} "
        f"btc_dd={base['benchmark_max_drawdown']:.2%} "
        f"severe_return={severe['total_return']:.2%}"
    )
    print("retuning=FORBIDDEN")
    print("rerun=FORBIDDEN")
    print("report=artifacts/m2_final_oos_2025.json")


if __name__ == "__main__":
    main()
