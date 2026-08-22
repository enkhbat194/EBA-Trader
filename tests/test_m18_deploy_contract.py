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
    assert "eba-trader-ui-v7" in worker
    assert "'./chart.js'" in worker
    assert "'./paper_ui.js'" in worker
    assert "'./momentum_ui.js'" in worker
    assert "'./m18_2.css'" in worker


def test_m18_3_ui_loads_paper_and_momentum_layers() -> None:
    page = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert '<script src="./paper_ui.js" defer></script>' in page
    assert '<script src="./momentum_ui.js" defer></script>' in page


def test_momentum_server_remains_demo_paper_only() -> None:
    server = (ROOT / "src/eba_trader/web_server_v2.py").read_text(encoding="utf-8")
    engine = (ROOT / "src/eba_trader/momentum_engine.py").read_text(encoding="utf-8")
    assert "EBA_BINANCE_DEMO_API_KEY" in server
    assert "EBA_BINANCE_DEMO_API_SECRET" in server
    assert "/api/momentum/step" in server
    assert "liveExecutionAllowed\": False" in engine
    assert "place_order" not in engine
    assert "change_leverage" not in engine
