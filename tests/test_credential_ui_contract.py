from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_credential_ui_uses_server_vault_and_never_browser_secret_storage() -> None:
    ui = (ROOT / "web" / "credential_ui.js").read_text(encoding="utf-8")
    research = (ROOT / "web" / "research_ui.js").read_text(encoding="utf-8")
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")

    assert "/api/demo/credential-status" in ui
    assert "/api/demo/credentials/save" in ui
    assert "/api/demo/credentials/delete" in ui
    assert "/api/demo/autoconnect" in ui
    assert "REPLACE SAVED DEMO KEY" in ui
    assert "DELETE SAVED DEMO KEY" in ui
    assert "localStorage" not in ui
    assert "sessionStorage" not in ui
    assert "credential_ui.js" in research
    assert "./credential_ui.js" in service_worker


def test_server_and_pwa_cache_advance_together_for_credential_release() -> None:
    server = (ROOT / "src" / "eba_trader" / "web_server_v2.py").read_text(encoding="utf-8")
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")

    assert 'APP_VERSION = "0.12.2"' in server
    assert 'APP_RELEASE = "LINODE-M7"' in server
    assert 'PWA_CACHE_VERSION = "eba-trader-ui-v15"' in server
    assert "CACHE_NAME = 'eba-trader-ui-v15'" in service_worker
    assert '"/api/demo/credentials/save"' in server
    assert '"/api/demo/credentials/delete"' in server
    assert 'liveExecutionAllowed": False' in server
