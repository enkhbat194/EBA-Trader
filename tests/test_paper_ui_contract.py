from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_paper_ui_is_loaded_after_base_app_and_has_no_live_order_path() -> None:
    chart = (ROOT / "web/chart.js").read_text(encoding="utf-8")
    paper = (ROOT / "web/paper_ui.js").read_text(encoding="utf-8")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "./paper_ui.js" in chart
    assert "'/api/paper/step'" in paper
    assert "'/api/paper/state'" in paper
    assert "'/api/paper/close'" in paper
    assert 'id="closePaperPosition" disabled' in html
    assert "place_order" not in paper
    assert "order_send" not in paper
    assert "localStorage" not in paper
    assert "sessionStorage" not in paper


def test_paper_history_and_chart_marker_surfaces_exist() -> None:
    paper = (ROOT / "web/paper_ui.js").read_text(encoding="utf-8")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'id="historyList"' in html
    assert 'id="paperTradeCount"' in html
    assert 'id="chartPositionSummary"' in html
    assert "result.markers" in paper
    assert "PAPER ENTRY" in (ROOT / "src/eba_trader/paper_engine.py").read_text(encoding="utf-8")
    assert "PAPER EXIT" in (ROOT / "src/eba_trader/paper_engine.py").read_text(encoding="utf-8")
