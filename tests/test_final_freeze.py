from __future__ import annotations

import json

import pytest

from eba_trader.execution_policy import EXECUTION_POLICY_NAME, EXECUTION_POLICY_VERSION
from eba_trader.final_freeze import freeze_final_oos_candidate, sha256_file

COSTS = {
    "base": {"fee_bps": 10.0, "slippage_bps": 5.0},
    "adverse": {"fee_bps": 10.0, "slippage_bps": 10.0},
    "severe": {"fee_bps": 15.0, "slippage_bps": 20.0},
}
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def signal_report(data_dir) -> dict[str, object]:
    return {
        "phase": "development_only",
        "symbol": "BTCUSDT",
        "interval": "15m",
        "data_dir": str(data_dir),
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "source_provenance": {
            "git_commit": COMMIT,
            "tracked_working_tree_clean": True,
        },
        "frozen_baseline": {"fast_ema": 20, "slow_ema": 50},
        "baseline": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "initial_cash": 1000.0,
            "cost_scenarios": COSTS,
            "windows": {
                "validation": {
                    "scenarios": {
                        "base": {
                            "trade_count": 40,
                            "total_return": 0.12,
                            "expectancy": 3.0,
                            "profit_factor": 1.25,
                            "average_win": 10.0,
                            "average_loss": -5.0,
                            "benchmark_relative_return": -0.05,
                            "max_drawdown": -0.12,
                            "benchmark_max_drawdown": -0.20,
                        },
                        "severe": {"total_return": 0.03},
                    }
                }
            },
        },
        "research_robustness": {
            "parameter_neighborhood": {"positive_expectancy_fraction": 0.67},
            "walk_forward": {
                "positive_test_fraction": 0.60,
                "positive_expectancy_fraction": 0.60,
                "drawdown_improvement_fraction": 0.60,
            },
        },
    }


def risk_report(
    signal_path,
    signal_verdict_path,
    research_path,
    validation_path,
) -> dict[str, object]:
    base = {
        "trade_count": 40,
        "total_return": 0.06,
        "expectancy": 1.5,
        "profit_factor": 1.3,
        "average_win": 6.0,
        "average_loss": -4.0,
        "max_drawdown": -0.04,
        "max_planned_risk_fraction": 0.005,
        "average_notional_fraction": 0.3,
        "max_drawdown_halted": False,
    }
    severe = dict(base)
    severe.update({"total_return": 0.02, "max_drawdown": -0.055})
    return {
        "phase": "risk_execution_development",
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "source_provenance": {
            "git_commit": COMMIT,
            "tracked_working_tree_clean": True,
        },
        "signal_development_report_sha256": sha256_file(signal_path),
        "signal_development_verdict_sha256": sha256_file(signal_verdict_path),
        "symbol": "BTCUSDT",
        "interval": "15m",
        "initial_cash": 1000.0,
        "strategy": {"fast_ema": 20, "slow_ema": 50},
        "execution_policy": {
            "version": EXECUTION_POLICY_VERSION,
            "name": EXECUTION_POLICY_NAME,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "risk_fraction": 0.005,
            "daily_loss_limit": 0.02,
            "max_drawdown_halt": 0.08,
            "spot_only": True,
            "leverage": 1.0,
            "take_profit": None,
            "normal_exit": "EMA cross-down at next bar open",
            "protective_exit": "ATR stop; adverse gaps execute at available bar open",
        },
        "cost_scenarios": COSTS,
        "datasets": {
            "research": {
                "path": str(research_path),
                "sha256": sha256_file(research_path),
                "start": "2021-01-01",
                "end_exclusive": "2024-01-01",
                "candle_count": 1,
            },
            "validation": {
                "path": str(validation_path),
                "sha256": sha256_file(validation_path),
                "start": "2024-01-01",
                "end_exclusive": "2025-01-01",
                "candle_count": 1,
            },
        },
        "windows": {"validation": {"scenarios": {"base": base, "severe": severe}}},
    }


def build_authority(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    research_path = data_dir / "btcusdt_15m_research.csv"
    validation_path = data_dir / "btcusdt_15m_validation.csv"
    research_path.write_text("research-data", encoding="utf-8")
    validation_path.write_text("validation-data", encoding="utf-8")

    signal_path = tmp_path / "signal.json"
    signal_path.write_text(json.dumps(signal_report(data_dir), sort_keys=True), encoding="utf-8")
    signal_verdict_path = tmp_path / "signal-verdict.json"
    signal_verdict_path.write_text(
        json.dumps(
            {
                "screening_version": 1,
                "status": "ELIGIBLE_FOR_FROZEN_OOS",
                "all_gates_passed": True,
                "development_report_sha256": sha256_file(signal_path),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    risk_path = tmp_path / "risk.json"
    risk_path.write_text(
        json.dumps(
            risk_report(signal_path, signal_verdict_path, research_path, validation_path),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    risk_verdict_path = tmp_path / "risk-verdict.json"
    risk_verdict_path.write_text(
        json.dumps(
            {
                "screening_version": 1,
                "status": "ELIGIBLE_FOR_FINAL_FROZEN_OOS",
                "all_gates_passed": True,
                "risk_execution_evidence_sha256": sha256_file(risk_path),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        data_dir,
        signal_path,
        signal_verdict_path,
        risk_path,
        risk_verdict_path,
        research_path,
        validation_path,
    )


def test_final_freeze_binds_both_evidence_layers(tmp_path) -> None:
    data_dir, signal, signal_v, risk, risk_v, _, _ = build_authority(tmp_path)
    freeze = tmp_path / "final-freeze.json"
    payload = freeze_final_oos_candidate(
        signal_path=signal,
        signal_verdict_path=signal_v,
        risk_path=risk,
        risk_verdict_path=risk_v,
        freeze_path=freeze,
    )
    assert payload["decision"] == "retain_final_risk_execution_for_frozen_oos"
    assert payload["source_git_commit"] == COMMIT
    assert payload["execution_policy"]["risk_fraction"] == 0.005
    assert payload["oos_cache"] == str(data_dir / "btcusdt_15m_out_of_sample.csv")
    assert freeze.exists()


def test_final_freeze_rejects_dataset_mutation(tmp_path) -> None:
    _, signal, signal_v, risk, risk_v, research_path, _ = build_authority(tmp_path)
    research_path.write_text("mutated", encoding="utf-8")
    with pytest.raises(RuntimeError, match="dataset changed"):
        freeze_final_oos_candidate(
            signal_path=signal,
            signal_verdict_path=signal_v,
            risk_path=risk,
            risk_verdict_path=risk_v,
            freeze_path=tmp_path / "freeze.json",
        )


def test_final_freeze_rejects_commit_mismatch(tmp_path) -> None:
    _, signal, signal_v, risk, risk_v, _, _ = build_authority(tmp_path)
    payload = json.loads(risk.read_text(encoding="utf-8"))
    payload["source_provenance"]["git_commit"] = "f" * 40
    risk.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    risk_v.write_text(
        json.dumps(
            {
                "screening_version": 1,
                "status": "ELIGIBLE_FOR_FINAL_FROZEN_OOS",
                "all_gates_passed": True,
                "risk_execution_evidence_sha256": sha256_file(risk),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="same Git commit"):
        freeze_final_oos_candidate(
            signal_path=signal,
            signal_verdict_path=signal_v,
            risk_path=risk,
            risk_verdict_path=risk_v,
            freeze_path=tmp_path / "freeze.json",
        )
