from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_screen_and_assets_are_wired_into_pwa() -> None:
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    research_js = (ROOT / "web" / "research_ui.js").read_text(encoding="utf-8")
    heartbeat_js = (ROOT / "web" / "scanner_heartbeat.js").read_text(encoding="utf-8")

    assert 'data-screen="research"' in index
    assert 'data-nav="research"' in index
    assert 'id="researchExperimentCount"' in index
    assert 'id="researchOosLock"' in index
    assert './research_ui.css' in index
    assert './research_ui.js' in index
    assert './research_ui.css' in service_worker
    assert './research_ui.js' in service_worker
    assert './scanner_heartbeat.js' in service_worker
    assert "'./scanner_heartbeat.js'" in research_js
    assert "'./credential_ui.js'" in research_js
    assert '/api/research/status' in research_js
    assert '/api/runner/status' in heartbeat_js
    assert "renameMetric('opportunityCount', 'Carry opportunity')" in heartbeat_js
    assert "renameMetric('expectedNetValue', 'Carry expected net')" in heartbeat_js
    assert 'Last server scan' in heartbeat_js
    assert 'Next expected scan' in heartbeat_js


def test_research_api_and_pwa_cache_versions_match() -> None:
    server = (ROOT / "src" / "eba_trader" / "web_server_v2.py").read_text(encoding="utf-8")
    service_worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")

    assert 'PWA_CACHE_VERSION = "eba-trader-ui-v15"' in server
    assert "CACHE_NAME = 'eba-trader-ui-v15'" in service_worker
    assert 'self.path == "/api/research/status"' in server
    assert 'self.path == "/api/runner/status"' in server
    assert 'liveExecutionAllowed": False' in server
