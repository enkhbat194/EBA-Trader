from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_is_demo_branch_free_and_health_checked() -> None:
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "name: eba-trader-demo" in blueprint
    assert "runtime: python" in blueprint
    assert "plan: free" in blueprint
    assert "region: singapore" in blueprint
    assert "branch: m18-fee-aware-execution-economics" in blueprint
    assert "healthCheckPath: /api/health" in blueprint
    assert "autoDeployTrigger: checksPass" in blueprint
    assert "PYTHONPATH=src python -m eba_trader.web_server_v2" in blueprint
    assert "value: 3.12.14" in blueprint


def test_python_runtime_is_pinned_to_ci_version() -> None:
    version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert version == "3.12.14"


def test_public_web_bridge_declares_security_headers() -> None:
    source = (ROOT / "src/eba_trader/web_server.py").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in source
    assert "X-Content-Type-Options" in source
    assert "X-Frame-Options" in source
    assert "Referrer-Policy" in source
    assert "Permissions-Policy" in source
    assert "Strict-Transport-Security" in source
    assert "connect-src 'self'" in source
    assert "frame-ancestors 'none'" in source


def test_service_worker_never_caches_api_responses() -> None:
    worker = (ROOT / "web/sw.js").read_text(encoding="utf-8")
    assert "startsWith('/api/')" in worker
    assert "event.respondWith(fetch(event.request))" in worker
    assert "eba-trader-ui-v10" in worker
    assert "'./chart.js'" in worker
    assert "'./paper_ui.js'" in worker
    assert "'./momentum_ui.js'" in worker
    assert "'./trade_detail.js'" in worker
    assert "'./trade_detail.css'" in worker
    assert "'./update_ui.js'" in worker
    assert "'./m18_2.css'" in worker


def test_m18_6_ui_loads_trade_detail_and_update_layers() -> None:
    page = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert '<script src="./paper_ui.js" defer></script>' in page
    assert '<script src="./momentum_ui.js" defer></script>' in page
    assert '<script src="./trade_detail.js" defer></script>' in page
    assert '<script src="./update_ui.js" defer></script>' in page
    assert '<link rel="stylesheet" href="./trade_detail.css">' in page


def test_momentum_server_remains_demo_paper_only() -> None:
    server = (ROOT / "src/eba_trader/web_server_v2.py").read_text(encoding="utf-8")
    engine = (ROOT / "src/eba_trader/momentum_engine.py").read_text(encoding="utf-8")
    assert "EBA_BINANCE_DEMO_API_KEY" in server
    assert "EBA_BINANCE_DEMO_API_SECRET" in server
    assert "/api/momentum/step" in server
    assert "liveExecutionAllowed\": False" in engine
    assert "place_order" not in engine
    assert "change_leverage" not in engine


def test_update_center_exposes_server_build_and_pwa_versions() -> None:
    server = (ROOT / "src/eba_trader/web_server_v2.py").read_text(encoding="utf-8")
    ui = (ROOT / "web/update_ui.js").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.9.1"' in server
    assert 'APP_RELEASE = "M18.6"' in server
    assert 'PWA_CACHE_VERSION = "eba-trader-ui-v10"' in server
    assert 'self.path == "/api/app-info"' in server
    assert "RENDER_GIT_COMMIT" in server
    assert "EBA_INSTALLED_APP_VERSION = '0.9.1'" in ui
    assert "EBA_INSTALLED_RELEASE = 'M18.6'" in ui
    assert "EBA_INSTALLED_PWA_CACHE = 'eba-trader-ui-v10'" in ui
    assert "UPDATE AVAILABLE" in ui
    assert "UP TO DATE" in ui


def test_trade_detail_terminal_exposes_fast_trade_controls() -> None:
    detail = (ROOT / "web/trade_detail.js").read_text(encoding="utf-8")
    css = (ROOT / "web/trade_detail.css").read_text(encoding="utf-8")
    assert "tradeDetailDialog" in detail
    assert "ENTRY" in detail
    assert "TAKE PROFIT" in detail
    assert "STOP LOSS" in detail
    assert "emaSeries" in detail
    assert "touchmove" in detail
    assert "openPositionCount" in detail
    assert "NEW ENTRY SIGNAL" in detail
    assert "trade-detail-dialog" in css
    assert "#tradeDetailChart" in css
