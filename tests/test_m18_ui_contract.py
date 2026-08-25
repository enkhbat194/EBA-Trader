from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


def test_dashboard_does_not_present_fake_account_values_before_connection() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "$25,430.68" not in html
    assert 'id="balanceValue">—<' in html
    assert 'id="todayPnlValue">—<' in html
    assert 'id="expectedNetValue">—<' in html


def test_paper_scanner_is_fail_closed_until_binance_demo_connection() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="startBot" disabled' in html
    assert "function hasConnectedBinanceDemo()" in javascript
    assert "CONNECT BINANCE DEMO" in javascript
    assert "PAPER SCANNER RUNNING" in javascript


def test_ui_keeps_live_and_secret_storage_locked() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="liveEnvironment" disabled' in html
    assert "localStorage" not in javascript
    assert "sessionStorage" not in javascript
    assert "environment: 'demo'" in javascript
    assert "place_order" not in javascript
    assert "order_send" not in javascript


def test_binance_demo_form_supports_public_paper_and_one_authenticated_pair() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "Fast Momentum paper does" in html
    assert "not</strong> require an API key" in html
    assert "Binance Demo API Key" in html
    assert "Binance Demo API Secret" in html
    assert "Optional Demo API key" in html
    assert "futuresApiKey" not in html
    assert "futuresApiSecret" not in html
    assert "futuresApiKey" not in javascript
    assert "futuresApiSecret" not in javascript
    assert "Binance Demo API key and secret are required." in javascript


def test_binance_demo_secret_fields_are_cleared_after_request() -> None:
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "apiKeyInput.value = '';" in javascript
    assert "apiSecretInput.value = '';" in javascript
    assert "credentials.apiKey = '';" in javascript
    assert "credentials.apiSecret = '';" in javascript


def test_demo_scanner_uses_only_opaque_session_token_after_connection() -> None:
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "let demoSessionToken = null;" in javascript
    assert "'/api/demo/snapshot'" in javascript
    assert "{ sessionToken: demoSessionToken }" in javascript
    assert "15_000" in javascript


def test_binance_demo_session_can_be_explicitly_disconnected() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="disconnectDemo"' in html
    assert "'/api/demo/disconnect'" in javascript
    assert "lockBinance('Binance Demo disconnected')" in javascript


def test_mt5_uses_local_pairing_bridge_without_broker_password_in_cloud_ui() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "MetaTrader 5" in html
    assert "MetaTrader 4" not in html
    assert 'id="createMt5Pair"' in html
    assert "Broker password stays on the PC" in html
    assert "Render" not in html
    assert "'/api/mt5/pair'" in javascript
    assert "'/api/mt5/state'" in javascript
    assert "'/api/mt5/disconnect'" in javascript
    assert "mtPassword" not in html
    assert "mtPassword" not in javascript


def test_live_chart_and_multi_market_controls_are_present() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    chart = (WEB_ROOT / "chart.js").read_text(encoding="utf-8")
    assert 'data-screen="chart"' in html
    assert 'id="marketChart"' in html
    assert "XAUUSD" in html
    assert "XAGUSD" in html
    assert "USOIL" in html
    assert "'/api/chart'" in javascript
    assert "window.EBAChart" in chart


def test_connection_markup_escapes_remote_text_before_inner_html() -> None:
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "function escapeHtml(value)" in javascript
    assert "escapeHtml(profile.detail)" in javascript
    assert "escapeHtml(profile.name)" in javascript
