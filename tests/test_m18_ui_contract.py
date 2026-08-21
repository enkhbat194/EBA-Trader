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


def test_binance_demo_form_is_explicitly_spot_testnet() -> None:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Spot Testnet API Key" in html
    assert "Spot Testnet API Secret" in html
