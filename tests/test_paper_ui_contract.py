from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_carry_ui_is_read_only_and_has_no_active_entry_path() -> None:
    chart = (ROOT / "web/chart.js").read_text(encoding="utf-8")
    paper = (ROOT / "web/paper_ui.js").read_text(encoding="utf-8")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")

    assert "./paper_ui.js" in chart
    assert "'/api/paper/state'" in paper
    assert "'/api/paper/step'" not in paper
    assert "legacyCarryRetired" in paper
    assert "newEntriesAllowed" in paper
    assert "legacyControls.hidden = true" in paper
    assert "close.hidden = true" in paper
    assert 'id="closePaperPosition" disabled' in html

    assert "place_order" not in paper
    assert "order_send" not in paper
    assert "localStorage" not in paper
    assert "sessionStorage" not in paper


def test_legacy_carry_surfaces_remain_compatible_but_markers_are_not_active() -> None:
    paper = (ROOT / "web/paper_ui.js").read_text(encoding="utf-8")
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    engine = (ROOT / "src/eba_trader/paper_engine.py").read_text(encoding="utf-8")

    assert 'id="historyList"' in html
    assert 'id="paperTradeCount"' in html
    assert 'id="chartPositionSummary"' in html
    assert "CARRY RETIRED" in paper
    assert "result.markers" not in paper
    assert "PAPER ENTRY" in engine
    assert "PAPER EXIT" in engine
