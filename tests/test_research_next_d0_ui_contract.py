from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_ui_exposes_next_d0_progress_without_promotion_authority() -> None:
    ui = (ROOT / "web" / "research_ui.js").read_text(encoding="utf-8")

    assert "strategyFactoryV2NextD0" in ui
    assert "Frozen discovery corpus" in ui
    assert "nextD0ProgressText" in ui
    assert "nextD0Service" in ui
    assert "SERVICE FAILED" in ui
    assert "Performance evaluation" in ui
    assert "LOCKED" in ui
    assert "NO · DISCOVERY ONLY" in ui
    assert "not a verified profitable strategy" in ui
    assert "performanceEvaluationAllowed === true" in ui
    assert "freshConfirmationEvidence === true" in ui


def test_next_d0_ui_is_read_only_and_pwa_refreshes_changed_assets() -> None:
    ui = (ROOT / "web" / "research_ui.js").read_text(encoding="utf-8")
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    server = (ROOT / "src" / "eba_trader" / "web_server_v2.py").read_text(encoding="utf-8")

    assert "fetch('/api/research/status', { cache: 'no-store' })" in ui
    assert "fetch('/api/research/status'," in ui
    assert "postJson(" not in ui
    assert "./research_ui.js" in service_worker
    assert "./research_ui.css" in service_worker
    assert "Refresh marker: next-D0 read-only progress UI" in service_worker
    assert "CACHE_NAME = 'eba-trader-ui-v15'" in service_worker
    assert 'PWA_CACHE_VERSION = "eba-trader-ui-v15"' in server
