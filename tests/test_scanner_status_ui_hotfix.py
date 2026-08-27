from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_settings_scanner_uses_fast_runner_truth_and_isolates_ui_errors() -> None:
    heartbeat = (ROOT / "web" / "scanner_heartbeat.js").read_text(encoding="utf-8")

    assert "status?.fastThreadAlive" in heartbeat
    assert "status?.lastFastScanAtMs" in heartbeat
    assert "status?.fastRunning" in heartbeat
    assert "renderSettingsApiFailure" in heartbeat
    assert "Runner API unavailable:" in heartbeat
    assert "UI sync warning:" in heartbeat
    assert "originalApplyRunnerStatus" in heartbeat
    assert "renderSettingsHealth(status, error)" in heartbeat
    assert "renderSettingsHealth(status);" in heartbeat


def test_ui_render_exception_is_not_labeled_as_runner_unreachable() -> None:
    heartbeat = (ROOT / "web" / "scanner_heartbeat.js").read_text(encoding="utf-8")

    guarded_apply = heartbeat.split(
        "ebaApplyRunnerStatus = function guardedApplyRunnerStatus(status)", 1
    )[1].split("ebaSyncRunnerStatus = async function", 1)[0]
    assert "UNREACHABLE" not in guarded_apply
    assert "UI sync warning:" not in guarded_apply  # warning text lives in the health renderer
    assert "renderSettingsHealth(status, error)" in guarded_apply

    guarded_sync = heartbeat.split(
        "ebaSyncRunnerStatus = async function guardedSyncRunnerStatus()", 1
    )[1].split("if (typeof ebaRunnerSyncTimer", 1)[0]
    assert "renderSettingsApiFailure(error)" in guarded_sync
    assert "ebaApplyRunnerStatus(status)" in guarded_sync


def test_current_shipped_javascript_has_no_stale_mt5_position_markup_reference() -> None:
    shipped = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "web").glob("*.js"))
    )

    assert "mt5PositionMarkup" not in shipped


def test_service_worker_revalidates_assets_instead_of_reseeding_stale_http_cache() -> None:
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")

    assert "fetch(asset, { cache: 'reload' })" in service_worker
    assert "fetch(event.request, { cache: 'no-store' })" in service_worker
    assert "cacheFreshAssets()" in service_worker
    assert "./scanner_heartbeat.js" in service_worker
