from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


def test_dashboard_does_not_present_fake_account_values_before_connection() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "$25,430.68" not in html
    assert 'id="balanceValue">—<' in html
    assert 'id="todayPnlValue">—<' in html
    assert 'id="expectedNetValue">—<' in html


def test_paper_bot_is_fail_closed_until_demo_connection() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="startBot" disabled' in html
    assert "function hasConnectedBinanceDemo()" in javascript
    assert "if (!hasConnectedBinanceDemo())" in javascript
    assert "CONNECT BINANCE DEMO" in javascript


def test_ui_keeps_live_and_secret_storage_locked() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="liveEnvironment" disabled' in html
    assert "localStorage" not in javascript
    assert "sessionStorage" not in javascript
    assert "environment: 'demo'" in javascript


def test_binance_demo_form_uses_one_unified_credential_pair() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "Binance Demo API Key" in html
    assert "Binance Demo API Secret" in html
    assert "One Demo key is used for both Spot and USD-M Futures" in html
    assert "futuresApiKey" not in html
    assert "futuresApiSecret" not in html
    assert "futuresApiKey" not in javascript
    assert "futuresApiSecret" not in javascript
    assert "Binance Demo API key and secret are required." in javascript


def test_binance_demo_secret_fields_are_cleared_after_request() -> None:
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "function clearCredentialInputs()" in javascript
    assert "apiKeyInput.value = '';" in javascript
    assert "apiSecretInput.value = '';" in javascript
    assert "credentials = null;" in javascript


def test_demo_scanner_uses_only_opaque_session_token_after_connection() -> None:
    javascript = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "let demoSessionToken = null;" in javascript
    assert "'/api/demo/snapshot'" in javascript
    assert "{ sessionToken: demoSessionToken }" in javascript
    assert "15_000" in javascript
    assert "PAPER SCANNER RUNNING" in javascript
