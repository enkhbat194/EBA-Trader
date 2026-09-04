from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .m5_study_policy import M5_FROZEN_OOS_END_EXCLUSIVE, M5_FROZEN_OOS_START
from .study_policy import FROZEN_OOS_END_EXCLUSIVE, FROZEN_OOS_START

INVENTORY_SCHEMA = "sfv2_historical_window_inventory_v1"
INVENTORY_AUTHORITY = "RESEARCH_BOUNDARY_ONLY"
EXPECTED_SYMBOL = "BTCUSDT"
EXPECTED_VENUE = "usd_m_futures"
EXPECTED_INTERVAL = "1m"
ALLOWED_CLASSIFICATIONS = frozenset(
    {"INSPECTED", "INSPECTED_QUARANTINE", "FROZEN_OOS", "PROTECTED_SF4"}
)
INSPECTED_CLASSIFICATIONS = frozenset({"INSPECTED", "INSPECTED_QUARANTINE"})
ABSOLUTE_BLOCK_CLASSIFICATIONS = frozenset({"FROZEN_OOS", "PROTECTED_SF4"})
EXPECTED_SF4_START = "2026-09-01T00:00:00Z"
EXPECTED_SF4_END = "2026-09-13T00:00:00Z"


def _parse_utc(value: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError("window timestamp is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("window timestamp must include timezone")
    return int(dt.astimezone(UTC).timestamp() * 1000)


def ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    if start_a >= end_a or start_b >= end_b:
        raise ValueError("ranges must have positive duration")
    return start_a < end_b and end_a > start_b


@dataclass(frozen=True, slots=True)
class HistoricalRange:
    range_id: str
    classification: str
    start_ms: int
    end_ms: int
    source: str


@dataclass(frozen=True, slots=True)
class HistoricalWindowInventory:
    symbol: str
    venue: str
    source_interval: str
    ranges: tuple[HistoricalRange, ...]
    authority: str = INVENTORY_AUTHORITY

    def conflicts(self, *, start_ms: int, end_ms: int) -> tuple[HistoricalRange, ...]:
        if start_ms >= end_ms:
            raise ValueError("candidate research range must have positive duration")
        return tuple(
            item
            for item in self.ranges
            if ranges_overlap(start_ms, end_ms, item.start_ms, item.end_ms)
        )


def _require_exact_hard_range(
    ranges: tuple[HistoricalRange, ...],
    *,
    range_id: str,
    classification: str,
    start: str,
    end: str,
) -> None:
    matches = [item for item in ranges if item.range_id == range_id]
    if len(matches) != 1:
        raise ValueError(f"historical inventory must contain exactly one {range_id}")
    item = matches[0]
    if item.classification != classification:
        raise ValueError(f"historical inventory classification changed for {range_id}")
    if item.start_ms != _parse_utc(start) or item.end_ms != _parse_utc(end):
        raise ValueError(f"historical inventory hard boundary changed for {range_id}")


def load_historical_window_inventory(path: str | Path) -> HistoricalWindowInventory:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read historical window inventory") from exc
    if not isinstance(payload, dict):
        raise ValueError("historical window inventory must be an object")

    expected_fields = {
        "schema",
        "symbol",
        "venue",
        "source_interval",
        "authority",
        "ranges",
        "rules",
    }
    if set(payload) != expected_fields:
        raise ValueError("historical window inventory fields changed")
    if payload["schema"] != INVENTORY_SCHEMA:
        raise ValueError("unsupported historical window inventory schema")
    if payload["authority"] != INVENTORY_AUTHORITY:
        raise ValueError("historical window inventory cannot grant evaluation authority")
    if payload["symbol"] != EXPECTED_SYMBOL:
        raise ValueError("historical window inventory symbol changed")
    if payload["venue"] != EXPECTED_VENUE:
        raise ValueError("historical window inventory venue changed")
    if payload["source_interval"] != EXPECTED_INTERVAL:
        raise ValueError("historical window inventory interval changed")

    raw_ranges = payload["ranges"]
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise ValueError("historical window inventory requires ranges")
    ranges: list[HistoricalRange] = []
    ids: set[str] = set()
    for row in raw_ranges:
        if not isinstance(row, dict) or set(row) != {
            "range_id",
            "classification",
            "start",
            "end",
            "source",
        }:
            raise ValueError("historical window inventory range fields changed")
        range_id = str(row["range_id"]).strip()
        classification = str(row["classification"]).strip()
        source = str(row["source"]).strip()
        if not range_id or range_id in ids:
            raise ValueError("historical range id is empty or duplicated")
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError(f"unsupported historical range classification: {classification}")
        if not source:
            raise ValueError("historical range source is required")
        start_ms = _parse_utc(str(row["start"]))
        end_ms = _parse_utc(str(row["end"]))
        if start_ms >= end_ms:
            raise ValueError("historical range must have positive duration")
        ids.add(range_id)
        ranges.append(HistoricalRange(range_id, classification, start_ms, end_ms, source))

    rules = payload["rules"]
    expected_rules = {
        "frozen_oos_never_allowed_for_discovery": True,
        "sf4_prospective_never_allowed_for_other_research": True,
        "inspected_reuse_must_be_explicit": True,
        "inspected_reuse_is_never_fresh_confirmation": True,
        "unlisted_range_is_not_automatically_confirmation_evidence": True,
    }
    if rules != expected_rules:
        raise ValueError("historical window inventory safety rules changed")

    frozen = tuple(ranges)
    _require_exact_hard_range(
        frozen,
        range_id="first-cycle-frozen-oos-2025",
        classification="FROZEN_OOS",
        start=f"{FROZEN_OOS_START}T00:00:00Z",
        end=f"{FROZEN_OOS_END_EXCLUSIVE}T00:00:00Z",
    )
    _require_exact_hard_range(
        frozen,
        range_id="m5-frozen-oos-2026",
        classification="FROZEN_OOS",
        start=M5_FROZEN_OOS_START,
        end=M5_FROZEN_OOS_END_EXCLUSIVE,
    )
    _require_exact_hard_range(
        frozen,
        range_id="sf4-prospective-replication",
        classification="PROTECTED_SF4",
        start=EXPECTED_SF4_START,
        end=EXPECTED_SF4_END,
    )

    return HistoricalWindowInventory(
        symbol=EXPECTED_SYMBOL,
        venue=EXPECTED_VENUE,
        source_interval=EXPECTED_INTERVAL,
        ranges=frozen,
    )


def assert_discovery_window_allowed(
    inventory: HistoricalWindowInventory,
    *,
    start_ms: int,
    end_ms: int,
    allow_inspected_reuse: bool = False,
) -> tuple[HistoricalRange, ...]:
    """Fail closed on protected evidence; inspected D0 reuse must be explicit.

    Returning inspected conflicts when reuse is explicitly allowed is intentional: callers can
    persist those range ids as contamination/search-history provenance. This function never
    labels any range fresh and grants no D1/OOS/execution authority.
    """

    conflicts = inventory.conflicts(start_ms=start_ms, end_ms=end_ms)
    absolute = [item for item in conflicts if item.classification in ABSOLUTE_BLOCK_CLASSIFICATIONS]
    if absolute:
        names = ", ".join(item.range_id for item in absolute)
        raise RuntimeError(f"discovery range overlaps protected evidence: {names}")
    inspected = [item for item in conflicts if item.classification in INSPECTED_CLASSIFICATIONS]
    if inspected and not allow_inspected_reuse:
        names = ", ".join(item.range_id for item in inspected)
        raise RuntimeError(
            "discovery range overlaps inspected evidence without explicit reuse: "
            f"{names}"
        )
    return tuple(inspected)


def assert_no_known_research_overlap(
    inventory: HistoricalWindowInventory,
    *,
    start_ms: int,
    end_ms: int,
) -> None:
    """Prove only that a range avoids every known inspected/protected range.

    A successful return is not confirmation authority and must never be interpreted as proof that
    the data is fresh, independent, statistically valid, or eligible for D1/Frozen OOS.
    """

    conflicts = inventory.conflicts(start_ms=start_ms, end_ms=end_ms)
    if conflicts:
        names = ", ".join(item.range_id for item in conflicts)
        raise RuntimeError(f"range overlaps known research evidence: {names}")
