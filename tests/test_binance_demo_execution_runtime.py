from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader import binance_demo_execution_runtime as runtime
from eba_trader.providers import CredentialEnvelope


class FakeVault:
    def load(self) -> CredentialEnvelope:
        return CredentialEnvelope(api_key="demo", api_secret="secret")


def _write_config(repo_root: Path) -> Path:
    path = repo_root / "config" / "binance_demo_execution_probe_v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "binance_demo_execution_probe_config_v1",
                "enabled": True,
                "probe_id": "runtime-test-v1",
                "symbol": "BTCUSDT",
                "target_notional_usdt": 25.0,
                "max_notional_usdt": 250.0,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_robustness(research_root: Path, *, complete: bool = True) -> Path:
    path = research_root / "m5-absorption-robustness-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "m5_absorption_robustness_runtime_status_v1",
                "phase": "COMPLETE" if complete else "RUNNING",
                "complete": complete,
                "safe": True,
                "candidateId": "absorption_020",
                "scenarioCount": 9,
                "robustnessId": "m5rob_test",
                "robustnessVerified": False,
                "developmentEvidenceOnly": True,
                "edgeClaimAllowed": False,
                "promotionAuthority": False,
                "frozenOosOpened": False,
                "m5FrozenOosOpened": False,
                "liveExecutionAllowed": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def _success_probe() -> dict[str, object]:
    return {
        "schema": "binance_demo_execution_proof_v1",
        "probeId": "runtime-test-v1",
        "phase": "COMPLETE",
        "passed": True,
        "environment": "demo",
        "venue": "Binance USD-M Futures Demo",
        "endpointHost": "demo-fapi.binance.com",
        "symbol": "BTCUSDT",
        "orderSubmissionAttempted": True,
        "openFilled": True,
        "closeFilled": True,
        "postPositionZero": True,
        "latency": {"openOrderAckMs": 30.0, "closeOrderAckMs": 35.0},
        "retryAutomatically": False,
        "realMoneyUsed": False,
        "liveExecutionAllowed": False,
    }


def test_runtime_executes_same_probe_once_then_reuses_terminal_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    research_root = tmp_path / "research"
    config_path = _write_config(repo_root)
    robustness_path = _write_robustness(research_root)
    proof_path = research_root / "binance-demo-execution-latest.json"
    calls = {"count": 0}

    def fake_probe(**_: object) -> dict[str, object]:
        calls["count"] += 1
        return _success_probe()

    monkeypatch.setattr(runtime, "run_demo_execution_probe", fake_probe)

    first = runtime.run_demo_execution_runtime(
        repo_root=repo_root,
        research_root=research_root,
        config_path=config_path,
        robustness_path=robustness_path,
        proof_path=proof_path,
        vault=FakeVault(),  # type: ignore[arg-type]
    )
    second = runtime.run_demo_execution_runtime(
        repo_root=repo_root,
        research_root=research_root,
        config_path=config_path,
        robustness_path=robustness_path,
        proof_path=proof_path,
        vault=FakeVault(),  # type: ignore[arg-type]
    )

    assert calls["count"] == 1
    assert first == second
    assert first["phase"] == "COMPLETE"
    assert first["passed"] is True
    assert first["robustnessVerified"] is False
    assert first["strategyPromotionAuthority"] is False
    assert first["liveExecutionAllowed"] is False


def test_runtime_never_replays_failed_probe_with_order_attempt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    research_root = tmp_path / "research"
    config_path = _write_config(repo_root)
    robustness_path = _write_robustness(research_root)
    proof_path = research_root / "binance-demo-execution-latest.json"
    calls = {"count": 0}

    def fake_probe(**_: object) -> dict[str, object]:
        calls["count"] += 1
        return {
            "schema": "binance_demo_execution_proof_v1",
            "probeId": "runtime-test-v1",
            "phase": "FAILED",
            "passed": False,
            "environment": "demo",
            "orderSubmissionAttempted": True,
            "positionMayRemainOpen": False,
            "retryAutomatically": False,
            "realMoneyUsed": False,
            "liveExecutionAllowed": False,
        }

    monkeypatch.setattr(runtime, "run_demo_execution_probe", fake_probe)

    first = runtime.run_demo_execution_runtime(
        repo_root=repo_root,
        research_root=research_root,
        config_path=config_path,
        robustness_path=robustness_path,
        proof_path=proof_path,
        vault=FakeVault(),  # type: ignore[arg-type]
    )
    second = runtime.run_demo_execution_runtime(
        repo_root=repo_root,
        research_root=research_root,
        config_path=config_path,
        robustness_path=robustness_path,
        proof_path=proof_path,
        vault=FakeVault(),  # type: ignore[arg-type]
    )

    assert first["phase"] == "FAILED"
    assert second["phase"] == "FAILED"
    assert calls["count"] == 1


def test_runtime_requires_completed_safe_robustness_before_demo_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    research_root = tmp_path / "research"
    config_path = _write_config(repo_root)
    robustness_path = _write_robustness(research_root, complete=False)
    calls = {"count": 0}

    def fake_probe(**_: object) -> dict[str, object]:
        calls["count"] += 1
        return _success_probe()

    monkeypatch.setattr(runtime, "run_demo_execution_probe", fake_probe)

    with pytest.raises(RuntimeError, match="not safely complete"):
        runtime.run_demo_execution_runtime(
            repo_root=repo_root,
            research_root=research_root,
            config_path=config_path,
            robustness_path=robustness_path,
            vault=FakeVault(),  # type: ignore[arg-type]
        )
    assert calls["count"] == 0


def test_interrupted_running_probe_is_blocked_instead_of_replayed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    research_root = tmp_path / "research"
    config_path = _write_config(repo_root)
    robustness_path = _write_robustness(research_root)
    proof_path = research_root / "binance-demo-execution-latest.json"
    proof_path.write_text(
        json.dumps(
            {
                "schema": "binance_demo_execution_runtime_status_v1",
                "probeId": "runtime-test-v1",
                "phase": "RUNNING",
                "orderSubmissionAttempted": True,
                "environment": "demo",
                "liveExecutionAllowed": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runtime,
        "run_demo_execution_probe",
        lambda **_: (_ for _ in ()).throw(AssertionError("must not replay")),
    )

    result = runtime.run_demo_execution_runtime(
        repo_root=repo_root,
        research_root=research_root,
        config_path=config_path,
        robustness_path=robustness_path,
        proof_path=proof_path,
        vault=FakeVault(),  # type: ignore[arg-type]
    )

    assert result["phase"] == "BLOCKED_REVIEW"
    assert result["orderSubmissionAttempted"] is True
    assert result["positionMayRemainOpen"] is True
    assert result["retryAutomatically"] is False


def test_maintenance_demo_failure_does_not_retry_or_fail_research_contract() -> None:
    script = Path("scripts/run_m5_research_maintenance_once.sh").read_text(encoding="utf-8")

    assert "-m eba_trader.binance_demo_execution_runtime" in script
    assert "demo_exit=$?" in script
    fatal_line = next(
        line
        for line in script.splitlines()
        if line.startswith("if [[ $ablation_exit")
    )
    assert "demo_exit" not in fatal_line
    assert "one-shot Binance DEMO" in script
