from __future__ import annotations

from dataclasses import dataclass

from .footprint_dataset import FootprintWindowRow
from .history import Candle, INTERVAL_MS, validate_candles


@dataclass(frozen=True, slots=True)
class AlignedCandleFootprint:
    candle: Candle
    footprint: FootprintWindowRow
    available_at_ms: int


def align_closed_footprints_to_candles(
    candles: tuple[Candle, ...] | list[Candle],
    footprints: tuple[FootprintWindowRow, ...] | list[FootprintWindowRow],
    *,
    interval: str,
    require_complete: bool = True,
) -> tuple[AlignedCandleFootprint, ...]:
    """Align only already-closed footprint windows to later candle opens.

    A footprint covering [t-step, t) is available at t and may therefore be attached to
    the candle opening at t. A footprint from the candle's own [t, t+step) window is never
    attached to that same candle, preventing future-event leakage.
    """
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    rows = validate_candles(candles)
    step = INTERVAL_MS[interval]

    by_end: dict[int, FootprintWindowRow] = {}
    for footprint in footprints:
        if footprint.end_ms - footprint.start_ms != step:
            raise ValueError("footprint width must match candle interval")
        if footprint.start_ms % step != 0 or footprint.end_ms % step != 0:
            raise ValueError("footprint boundaries must align to candle interval")
        if footprint.end_ms in by_end:
            raise ValueError("duplicate footprint availability timestamp")
        by_end[footprint.end_ms] = footprint

    aligned: list[AlignedCandleFootprint] = []
    missing: list[int] = []
    for candle in rows:
        footprint = by_end.get(candle.open_time_ms)
        if footprint is None:
            missing.append(candle.open_time_ms)
            continue
        if footprint.end_ms > candle.open_time_ms:
            raise RuntimeError("footprint is not yet available at candle open")
        aligned.append(
            AlignedCandleFootprint(
                candle=candle,
                footprint=footprint,
                available_at_ms=footprint.end_ms,
            )
        )

    if require_complete and missing:
        raise ValueError(
            "missing closed footprint for candle opens: "
            + ", ".join(str(value) for value in missing[:5])
        )
    return tuple(aligned)
