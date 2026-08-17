from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .study_policy import (
    FIRST_CYCLE_INTERVAL,
    FIRST_CYCLE_SYMBOL,
    FROZEN_OOS_END_EXCLUSIVE,
    FROZEN_OOS_START,
)


def _parse_utc_ms(value: str) -> int:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.astimezone(UTC).timestamp() * 1000)


FIRST_CYCLE_OOS_START_MS = _parse_utc_ms(FROZEN_OOS_START)
FIRST_CYCLE_OOS_END_MS = _parse_utc_ms(FROZEN_OOS_END_EXCLUSIVE)


@dataclass(frozen=True, slots=True)
class HoldoutOverlap:
    symbol: str
    interval: str
    start_ms: int
    end_ms: int


def ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    if start_a >= end_a or start_b >= end_b:
        raise ValueError("Ranges must have positive duration")
    return start_a < end_b and end_a > start_b


def overlaps_first_cycle_oos(
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> bool:
    """Return True only for the frozen BTCUSDT/15m first-cycle holdout overlap."""
    if symbol.upper() != FIRST_CYCLE_SYMBOL or interval != FIRST_CYCLE_INTERVAL:
        return False
    return ranges_overlap(
        start_ms,
        end_ms,
        FIRST_CYCLE_OOS_START_MS,
        FIRST_CYCLE_OOS_END_MS,
    )


def assert_not_first_cycle_oos_overlap(
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    context: str,
) -> None:
    if overlaps_first_cycle_oos(
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
    ):
        raise RuntimeError(
            f"{context} overlaps the frozen first-cycle 2025 OOS window. "
            "Use only the authorized frozen OOS path after development screening and freeze."
        )
