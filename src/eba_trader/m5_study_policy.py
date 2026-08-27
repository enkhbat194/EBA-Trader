from __future__ import annotations

from dataclasses import dataclass

from .history import INTERVAL_MS, parse_utc
from .research_evidence import canonical_json, sha256_text

M5_STUDY_POLICY_NAME = "m5_btcusdt_usdm_orderflow_chronological"
M5_STUDY_POLICY_VERSION = 1
M5_SYMBOL = "BTCUSDT"
M5_VENUE = "usd_m_futures"
M5_INTERVAL = "1m"
M5_DEVELOPMENT_START = "2026-07-01T00:00:00Z"
M5_DEVELOPMENT_END_EXCLUSIVE = "2026-08-15T00:00:00Z"
M5_FROZEN_OOS_START = "2026-08-15T00:00:00Z"
M5_FROZEN_OOS_END_EXCLUSIVE = "2026-08-22T00:00:00Z"
M5_FORWARD_START = M5_FROZEN_OOS_END_EXCLUSIVE
MAX_M5_CORPUS_WINDOWS = 24


def _range_overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    if start_a >= end_a or start_b >= end_b:
        raise ValueError("study ranges must have positive duration")
    return start_a < end_b and end_a > start_b


@dataclass(frozen=True, slots=True)
class M5StudyWindow:
    name: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("M5 study window name is required")
        if self.start_ms >= self.end_ms:
            raise ValueError("M5 study window must have positive duration")
        step = INTERVAL_MS[M5_INTERVAL]
        if self.start_ms % step != 0 or self.end_ms % step != 0:
            raise ValueError("M5 study window must align to the policy interval")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }


@dataclass(frozen=True, slots=True)
class M5OrderFlowStudyPolicy:
    name: str
    version: int
    symbol: str
    venue: str
    interval: str
    development_start_ms: int
    development_end_ms: int
    frozen_oos_start_ms: int
    frozen_oos_end_ms: int
    forward_start_ms: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("M5 study policy name is required")
        if self.version < 1:
            raise ValueError("M5 study policy version must be >= 1")
        if self.symbol != M5_SYMBOL:
            raise ValueError(f"M5 study policy symbol must be {M5_SYMBOL}")
        if self.venue != M5_VENUE:
            raise ValueError(f"M5 study policy venue must be {M5_VENUE}")
        if self.interval != M5_INTERVAL:
            raise ValueError(f"M5 study policy interval must be {M5_INTERVAL}")
        if not (
            self.development_start_ms
            < self.development_end_ms
            == self.frozen_oos_start_ms
            < self.frozen_oos_end_ms
            == self.forward_start_ms
        ):
            raise ValueError(
                "M5 study chronology must be development -> frozen OOS -> forward"
            )
        step = INTERVAL_MS[self.interval]
        for value in (
            self.development_start_ms,
            self.development_end_ms,
            self.frozen_oos_start_ms,
            self.frozen_oos_end_ms,
            self.forward_start_ms,
        ):
            if value % step != 0:
                raise ValueError("M5 study boundaries must align to the policy interval")

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "development_start_ms": self.development_start_ms,
            "development_end_ms": self.development_end_ms,
            "frozen_oos_start_ms": self.frozen_oos_start_ms,
            "frozen_oos_end_ms": self.frozen_oos_end_ms,
            "forward_start_ms": self.forward_start_ms,
        }

    @property
    def policy_id(self) -> str:
        return f"m5policy_{sha256_text(canonical_json(self.as_dict()))[:24]}"


DEFAULT_M5_STUDY_POLICY = M5OrderFlowStudyPolicy(
    name=M5_STUDY_POLICY_NAME,
    version=M5_STUDY_POLICY_VERSION,
    symbol=M5_SYMBOL,
    venue=M5_VENUE,
    interval=M5_INTERVAL,
    development_start_ms=parse_utc(M5_DEVELOPMENT_START),
    development_end_ms=parse_utc(M5_DEVELOPMENT_END_EXCLUSIVE),
    frozen_oos_start_ms=parse_utc(M5_FROZEN_OOS_START),
    frozen_oos_end_ms=parse_utc(M5_FROZEN_OOS_END_EXCLUSIVE),
    forward_start_ms=parse_utc(M5_FORWARD_START),
)


def overlaps_m5_frozen_oos(
    *,
    symbol: str,
    venue: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> bool:
    policy = DEFAULT_M5_STUDY_POLICY
    if symbol.strip().upper() != policy.symbol:
        return False
    if venue.strip().lower() != policy.venue:
        return False
    if interval.strip() != policy.interval:
        return False
    return _range_overlaps(
        start_ms,
        end_ms,
        policy.frozen_oos_start_ms,
        policy.frozen_oos_end_ms,
    )


def assert_not_m5_frozen_oos_overlap(
    *,
    symbol: str,
    venue: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    context: str,
) -> None:
    if overlaps_m5_frozen_oos(
        symbol=symbol,
        venue=venue,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
    ):
        raise RuntimeError(
            f"{context} overlaps sealed M5 frozen OOS "
            f"{M5_FROZEN_OOS_START} -> {M5_FROZEN_OOS_END_EXCLUSIVE}. "
            "Normal development acquisition has no OOS authority."
        )


def assert_m5_development_range(
    *,
    symbol: str,
    venue: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    context: str,
) -> None:
    policy = DEFAULT_M5_STUDY_POLICY
    if symbol.strip().upper() != policy.symbol:
        raise ValueError(f"{context} requires symbol {policy.symbol}")
    if venue.strip().lower() != policy.venue:
        raise ValueError(f"{context} requires venue {policy.venue}")
    if interval.strip() != policy.interval:
        raise ValueError(f"{context} requires interval {policy.interval}")
    if start_ms >= end_ms:
        raise ValueError(f"{context} requires a positive time range")
    assert_not_m5_frozen_oos_overlap(
        symbol=policy.symbol,
        venue=policy.venue,
        interval=policy.interval,
        start_ms=start_ms,
        end_ms=end_ms,
        context=context,
    )
    if start_ms < policy.development_start_ms or end_ms > policy.development_end_ms:
        raise RuntimeError(
            f"{context} is outside sealed M5 development range "
            f"{M5_DEVELOPMENT_START} -> {M5_DEVELOPMENT_END_EXCLUSIVE}."
        )


@dataclass(frozen=True, slots=True)
class M5DevelopmentCorpusSpec:
    policy_id: str
    windows: tuple[M5StudyWindow, ...]

    def __post_init__(self) -> None:
        if self.policy_id != DEFAULT_M5_STUDY_POLICY.policy_id:
            raise ValueError("M5 corpus must reference the sealed default study policy")
        if not self.windows:
            raise ValueError("M5 development corpus requires at least one window")
        if len(self.windows) > MAX_M5_CORPUS_WINDOWS:
            raise ValueError(
                f"M5 development corpus exceeds hard cap {MAX_M5_CORPUS_WINDOWS}"
            )
        names = [window.name for window in self.windows]
        if len(names) != len(set(names)):
            raise ValueError("M5 development corpus window names must be unique")

        ordered = sorted(self.windows, key=lambda item: (item.start_ms, item.end_ms, item.name))
        if tuple(ordered) != self.windows:
            raise ValueError("M5 development corpus windows must be chronological")

        previous_end: int | None = None
        for window in self.windows:
            assert_m5_development_range(
                symbol=M5_SYMBOL,
                venue=M5_VENUE,
                interval=M5_INTERVAL,
                start_ms=window.start_ms,
                end_ms=window.end_ms,
                context=f"M5 corpus window {window.name}",
            )
            if previous_end is not None and window.start_ms < previous_end:
                raise ValueError("M5 development corpus windows cannot overlap")
            previous_end = window.end_ms

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "m5_development_corpus_v1",
            "policy_id": self.policy_id,
            "windows": [window.as_dict() for window in self.windows],
        }

    @property
    def corpus_id(self) -> str:
        return f"m5corpus_{sha256_text(canonical_json(self.as_dict()))[:24]}"


def _window(name: str, start: str, end: str) -> M5StudyWindow:
    return M5StudyWindow(name=name, start_ms=parse_utc(start), end_ms=parse_utc(end))


# Pre-registered fresh development windows. The already-inspected 2026-08-01 proof
# window is deliberately not part of this corpus so the corpus can provide new
# development evidence instead of repeatedly tuning on the original smoke window.
DEFAULT_M5_DEVELOPMENT_CORPUS = M5DevelopmentCorpusSpec(
    policy_id=DEFAULT_M5_STUDY_POLICY.policy_id,
    windows=(
        _window("dev-01", "2026-07-02T00:00:00Z", "2026-07-02T04:00:00Z"),
        _window("dev-02", "2026-07-06T08:00:00Z", "2026-07-06T12:00:00Z"),
        _window("dev-03", "2026-07-10T16:00:00Z", "2026-07-10T20:00:00Z"),
        _window("dev-04", "2026-07-14T00:00:00Z", "2026-07-14T04:00:00Z"),
        _window("dev-05", "2026-07-18T08:00:00Z", "2026-07-18T12:00:00Z"),
        _window("dev-06", "2026-07-22T16:00:00Z", "2026-07-22T20:00:00Z"),
        _window("dev-07", "2026-07-26T00:00:00Z", "2026-07-26T04:00:00Z"),
        _window("dev-08", "2026-07-30T08:00:00Z", "2026-07-30T12:00:00Z"),
        _window("dev-09", "2026-08-03T16:00:00Z", "2026-08-03T20:00:00Z"),
        _window("dev-10", "2026-08-07T00:00:00Z", "2026-08-07T04:00:00Z"),
        _window("dev-11", "2026-08-11T08:00:00Z", "2026-08-11T12:00:00Z"),
        _window("dev-12", "2026-08-14T16:00:00Z", "2026-08-14T20:00:00Z"),
    ),
)
