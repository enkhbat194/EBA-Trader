from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from eba_trader.persistence import PositionRecord, TradeLedger

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fast_restart_proof.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fast_restart_proof_test_module", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runner(position_id: str | None) -> dict[str, object]:
    position = {"position_id": position_id} if position_id is not None else None
    return {
        "ok": True,
        "liveExecutionAllowed": False,
        "fastState": {"openPosition": position},
    }


def _open_fast_position(ledger: TradeLedger, position_id: str) -> None:
    ledger.upsert_position(
        PositionRecord(
            position_id=position_id,
            symbol="BTCUSDT",
            side="LONG",
            status="OPEN",
            entry_price=100.0,
            quantity=1.0,
            leverage=5.0,
            take_profit=105.0,
            stop_loss=95.0,
            opened_at="2026-08-27T04:00:00+00:00",
            strategy="FAST_MOMENTUM",
            metadata={"sessionKey": "server-autonomous-demo"},
        )
    )
    ledger.append_event(
        "FAST_MOMENTUM_OPEN",
        position_id=position_id,
        payload={"side": "LONG"},
    )


def test_waits_for_natural_position_without_restart(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    ledger_path = tmp_path / "ledger.db"
    state_path = tmp_path / "proof.json"
    TradeLedger(ledger_path)
    restarted = False

    monkeypatch.setattr(module, "_runner_status", lambda: _runner(None))

    def restart() -> None:
        nonlocal restarted
        restarted = True

    monkeypatch.setattr(module, "_restart_web", restart)
    result = module.advance(state_path=state_path, ledger_path=ledger_path)

    assert result["phase"] == "WAITING_FOR_OPEN"
    assert result["passed"] is False
    assert restarted is False


def test_open_recovery_mark_close_path_is_persisted(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    ledger_path = tmp_path / "ledger.db"
    state_path = tmp_path / "proof.json"
    ledger = TradeLedger(ledger_path)
    position_id = "fast-proof-1"
    _open_fast_position(ledger, position_id)

    statuses = iter((_runner(position_id), _runner(position_id)))
    monkeypatch.setattr(module, "_runner_status", lambda: next(statuses))
    monkeypatch.setattr(module, "_restart_web", lambda: None)

    recovered = module.advance(state_path=state_path, ledger_path=ledger_path)
    assert recovered["phase"] == "WAITING_FOR_MARK_CLOSE"
    assert recovered["openEventProved"] is True
    assert recovered["recoveryProved"] is True
    assert recovered["positionId"] == position_id

    ledger.append_event(
        "FAST_MOMENTUM_MARK",
        position_id=position_id,
        payload={"markPrice": 101.0},
    )
    marked = module.advance(state_path=state_path, ledger_path=ledger_path)
    assert marked["postRestartMarkSeen"] is True
    assert marked["passed"] is False

    ledger.upsert_position(
        PositionRecord(
            position_id=position_id,
            symbol="BTCUSDT",
            side="LONG",
            status="CLOSED",
            entry_price=100.0,
            quantity=1.0,
            leverage=5.0,
            take_profit=105.0,
            stop_loss=95.0,
            opened_at="2026-08-27T04:00:00+00:00",
            closed_at="2026-08-27T04:05:00+00:00",
            exit_price=102.0,
            realized_pnl=1.0,
            strategy="FAST_MOMENTUM",
            metadata={"sessionKey": "server-autonomous-demo"},
        )
    )
    ledger.append_event(
        "FAST_MOMENTUM_CLOSE",
        position_id=position_id,
        payload={"exitReason": "TAKE_PROFIT"},
    )
    final = module.advance(state_path=state_path, ledger_path=ledger_path)

    assert final["phase"] == "PASS"
    assert final["passed"] is True
    assert final["postRestartMarkSeen"] is True
    assert final["postRestartCloseSeen"] is True
    assert final["liveExecutionAllowed"] is False


def test_systemd_watcher_is_delayed_bounded_and_persistent() -> None:
    service = (ROOT / "deploy/systemd/eba-fast-restart-proof.service").read_text(
        encoding="utf-8"
    )
    timer = (ROOT / "deploy/systemd/eba-fast-restart-proof.timer").read_text(
        encoding="utf-8"
    )
    install = (ROOT / "scripts/install_linode_runtime.sh").read_text(encoding="utf-8")
    update = (ROOT / "scripts/update_linode_runtime.sh").read_text(encoding="utf-8")

    assert "scripts/fast_restart_proof.py" in service
    assert "--ledger /var/lib/eba-trader/eba_trader.db" in service
    assert "ReadWritePaths=/var/lib/eba-trader/proofs" in service
    assert "OnActiveSec=2min" in timer
    assert "OnUnitActiveSec=1min" in timer
    assert "Persistent=true" in timer
    for script in (install, update):
        assert "eba-fast-restart-proof.service" in script
        assert "eba-fast-restart-proof.timer" in script
