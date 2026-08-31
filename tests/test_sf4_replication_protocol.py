from __future__ import annotations

import json
from pathlib import Path

import pytest

from eba_trader.sf4_replication_protocol import (
    EVALUATION_NOT_BEFORE_MS,
    PLANNED_MULTIPLE_TESTING_BUDGET,
    load_sf4_replication_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "sf4_two_hypothesis_replication_v1.json"


def _payload() -> dict[str, object]:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_canonical_replication_protocol_freezes_two_hypotheses() -> None:
    protocol = load_sf4_replication_protocol(PROTOCOL_PATH)
    assert protocol.planned_multiple_testing_budget == PLANNED_MULTIPLE_TESTING_BUDGET == 48
    assert len(protocol.candidates) == 2
    assert [candidate.source_candidate_id for candidate in protocol.candidates] == [
        "s3_vsm_s150",
        "s3_cex_s075",
    ]
    assert len(protocol.corpus.windows) == 12
    assert protocol.evaluation_not_before_ms == EVALUATION_NOT_BEFORE_MS


def test_replication_cannot_be_evaluated_early() -> None:
    protocol = load_sf4_replication_protocol(PROTOCOL_PATH)
    with pytest.raises(RuntimeError, match="before all prospective windows close"):
        protocol.assert_evaluation_time(EVALUATION_NOT_BEFORE_MS - 1)
    protocol.assert_evaluation_time(EVALUATION_NOT_BEFORE_MS)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prospective_only", False),
        ("parameter_tuning_allowed", True),
        ("combine_with_sf3_for_qualification", True),
        ("planned_multiple_testing_budget", 2),
    ],
)
def test_top_level_safety_weakening_is_rejected(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError):
        load_sf4_replication_protocol(_write(tmp_path, payload))


def test_frozen_oos_authority_cannot_be_enabled(tmp_path: Path) -> None:
    payload = _payload()
    safety = dict(payload["safety"])
    safety["frozen_oos_allowed"] = True
    payload["safety"] = safety
    with pytest.raises(ValueError, match="safety locks"):
        load_sf4_replication_protocol(_write(tmp_path, payload))


def test_old_sf3_trade_count_cannot_be_added(tmp_path: Path) -> None:
    payload = _payload()
    control = dict(payload["selection_bias_control"])
    control["sf3_trade_count_may_not_be_added_to_replication_trade_count"] = False
    payload["selection_bias_control"] = control
    with pytest.raises(ValueError, match="selection-bias"):
        load_sf4_replication_protocol(_write(tmp_path, payload))


def test_candidate_parameters_are_immutable(tmp_path: Path) -> None:
    payload = _payload()
    candidates = [dict(item) for item in payload["candidates"]]
    first = dict(candidates[0])
    parameters = dict(first["parameters"])
    parameters["volume_multiple"] = 1.4
    first["parameters"] = parameters
    candidates[0] = first
    payload["candidates"] = candidates
    with pytest.raises(ValueError, match="candidate contract changed"):
        load_sf4_replication_protocol(_write(tmp_path, payload))


def test_replication_windows_cannot_move_back_into_inspected_history(tmp_path: Path) -> None:
    payload = _payload()
    windows = [dict(item) for item in payload["replication_windows"]]
    first = dict(windows[0])
    first["start"] = "2026-08-31T00:00:00Z"
    first["end"] = "2026-09-01T00:00:00Z"
    windows[0] = first
    payload["replication_windows"] = windows
    with pytest.raises(ValueError):
        load_sf4_replication_protocol(_write(tmp_path, payload))
