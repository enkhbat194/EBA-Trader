from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from .history import Candle
from .orderflow_feature_dataset import OrderFlowFeatureRow
from .research_evidence import canonical_json, sha256_text
from .strategy_discovery_batch import (
    DiscoveryBatchContext,
    DiscoveryBatchSummary,
    run_discovery_batch,
)
from .strategy_discovery_v2 import (
    BehavioralFingerprint,
    DiscoveryCandidate,
    DiscoveryTrialLedger,
    select_behavioral_representatives,
)
from .strategy_factory_v2_d0 import D0DatasetManifest, D0TemporalStratum, build_d0_dataset_manifest
from .strategy_factory_v2_evaluator import DiscoveryDatasetV2, make_d0_candidate_evaluator

LOW_FIDELITY_SCHEMA = "strategy_factory_v2_low_fidelity_v1"
LOW_FIDELITY_AUTHORITY = "DISCOVERY_ONLY"
DEFAULT_WARMUP_BARS = 96
REQUIRED_SELECTION_METRICS = (
    "total_return",
    "expectancy",
    "trade_count",
    "benchmark_relative_return",
    "max_drawdown",
    "total_cost",
    "exposure",
    "turnover_round_trips_per_1000_bars",
)


@dataclass(frozen=True, slots=True)
class LowFidelityStratumDataset:
    stratum: D0TemporalStratum
    dataset: DiscoveryDatasetV2
    dataset_sha256: str
    parent_dataset_sha256: str
    warmup_start_index: int

    def __post_init__(self) -> None:
        if not self.dataset_sha256.strip() or not self.parent_dataset_sha256.strip():
            raise ValueError("low-fidelity dataset identities are required")
        if self.warmup_start_index < 0 or self.warmup_start_index > self.stratum.start_index:
            raise ValueError("invalid low-fidelity warmup boundary")
        if self.dataset.trade_start_time_ms != self.stratum.start_ms:
            raise ValueError("low-fidelity trade boundary must equal declared stratum start")

    @property
    def fidelity(self) -> str:
        return f"d0-low-v1:{self.stratum.stratum_id}"


@dataclass(frozen=True, slots=True)
class LowFidelityCandidateSummary:
    candidate_id: str
    family_id: str
    complete: bool
    rejected: bool
    stratum_count: int
    mean_total_return: float | None
    mean_expectancy: float | None
    total_trade_count: int
    mean_benchmark_relative_return: float | None
    mean_max_drawdown: float | None
    mean_total_cost: float | None
    mean_exposure: float | None
    mean_turnover: float | None
    behavior: BehavioralFingerprint | None


@dataclass(frozen=True, slots=True)
class LowFidelityDiscoveryReport:
    expected_strata: tuple[str, ...]
    candidates: tuple[LowFidelityCandidateSummary, ...]
    representative_candidate_ids: tuple[str, ...]

    @property
    def complete_candidate_count(self) -> int:
        return sum(item.complete for item in self.candidates)

    @property
    def rejected_candidate_count(self) -> int:
        return sum(item.rejected for item in self.candidates)


def _contiguous_warmup_start(
    candles: tuple[Candle, ...],
    *,
    stratum_start_index: int,
    warmup_bars: int,
) -> int:
    """Walk backward only across truly contiguous candles.

    D0 may concatenate independently sampled historical windows. A requested warmup must never
    bridge a temporal gap and make indicators treat days-apart observations as adjacent bars.
    """

    start = stratum_start_index
    remaining = warmup_bars
    while start > 0 and remaining > 0:
        previous = candles[start - 1]
        current = candles[start]
        if previous.close_time_ms + 1 != current.open_time_ms:
            break
        start -= 1
        remaining -= 1
    return start


def materialize_low_fidelity_strata(
    *,
    manifest: D0DatasetManifest,
    candles: tuple[Candle, ...],
    orderflow_rows: tuple[OrderFlowFeatureRow, ...] = (),
    warmup_bars: int = DEFAULT_WARMUP_BARS,
) -> tuple[LowFidelityStratumDataset, ...]:
    """Materialize every declared D0 stratum with causal pre-stratum warmup.

    The parent manifest is recomputed from supplied content before any slice is returned. This
    prevents a caller from pairing a trusted dataset SHA with different in-memory data. Warmup
    rows are context only; trading begins exactly at each declared stratum start. Warmup never
    crosses a temporal discontinuity between independently sampled source windows.
    """

    if warmup_bars < 0:
        raise ValueError("warmup_bars must be non-negative")
    rebuilt = build_d0_dataset_manifest(
        symbol=manifest.symbol,
        venue=manifest.venue,
        interval=manifest.interval,
        candles=candles,
        orderflow_rows=orderflow_rows,
        temporal_strata=len(manifest.temporal_strata),
    )
    if rebuilt.as_dict() != manifest.as_dict():
        raise ValueError("D0 manifest does not match supplied dataset content")

    output: list[LowFidelityStratumDataset] = []
    for stratum in manifest.temporal_strata:
        warmup_start = _contiguous_warmup_start(
            candles,
            stratum_start_index=stratum.start_index,
            warmup_bars=warmup_bars,
        )
        candle_slice = candles[warmup_start : stratum.end_index_exclusive]
        orderflow_slice = (
            orderflow_rows[warmup_start : stratum.end_index_exclusive] if orderflow_rows else ()
        )
        identity = {
            "schema": LOW_FIDELITY_SCHEMA,
            "authority": LOW_FIDELITY_AUTHORITY,
            "parent_dataset_sha256": manifest.dataset_sha256,
            "stratum": stratum.as_dict(),
            "warmup_start_index": warmup_start,
            "warmup_bars_requested": warmup_bars,
            "candle_sha256": sha256_text(
                canonical_json(
                    [
                        {
                            "open_time_ms": item.open_time_ms,
                            "close_time_ms": item.close_time_ms,
                            "open": item.open,
                            "high": item.high,
                            "low": item.low,
                            "close": item.close,
                            "volume": item.volume,
                            "quote_volume": item.quote_volume,
                            "trade_count": item.trade_count,
                        }
                        for item in candle_slice
                    ]
                )
            ),
        }
        if orderflow_slice:
            identity["orderflow_sha256"] = sha256_text(
                canonical_json(
                    [
                        {
                            "open_time_ms": row.candle.open_time_ms,
                            "footprint_available_at_ms": row.footprint_available_at_ms,
                            "of_buy_volume": row.of_buy_volume,
                            "of_sell_volume": row.of_sell_volume,
                            "of_delta": row.of_delta,
                            "of_delta_ratio": row.of_delta_ratio,
                            "of_cvd": row.of_cvd,
                            "of_poc_price": row.of_poc_price,
                        }
                        for row in orderflow_slice
                    ]
                )
            )
        dataset_sha = sha256_text(canonical_json(identity))
        dataset = DiscoveryDatasetV2(
            candles=candle_slice,
            orderflow_rows=orderflow_slice,
            trade_start_time_ms=stratum.start_ms,
        )
        output.append(
            LowFidelityStratumDataset(
                stratum=stratum,
                dataset=dataset,
                dataset_sha256=dataset_sha,
                parent_dataset_sha256=manifest.dataset_sha256,
                warmup_start_index=warmup_start,
            )
        )
    return tuple(output)


def run_low_fidelity_stratum(
    *,
    ledger: DiscoveryTrialLedger,
    campaign_id: str,
    source_code_sha: str,
    search_round: int,
    max_compute_ms: int,
    candidates: Sequence[DiscoveryCandidate],
    stratum_dataset: LowFidelityStratumDataset,
) -> DiscoveryBatchSummary:
    """Run one declared stratum through the immutable discovery ledger."""

    context = DiscoveryBatchContext(
        campaign_id=campaign_id,
        dataset_sha256=stratum_dataset.dataset_sha256,
        source_code_sha=source_code_sha,
        fidelity=stratum_dataset.fidelity,
        search_round=search_round,
        max_compute_ms=max_compute_ms,
    )
    return run_discovery_batch(
        ledger=ledger,
        context=context,
        candidates=candidates,
        evaluator=make_d0_candidate_evaluator(stratum_dataset.dataset),
    )


def build_low_fidelity_report(
    *,
    trials: Sequence[Mapping[str, Any]],
    expected_strata: Sequence[str],
    behavioral_similarity_threshold: float = 0.90,
) -> LowFidelityDiscoveryReport:
    """Aggregate completed D0 strata and deduplicate behavior without promotion authority.

    Only candidates with one terminal trial for every expected stratum are marked complete.
    Rejected or incomplete candidates never expose aggregate selection economics and never enter
    behavioral representative selection. Complete non-rejected candidates must expose the full
    fixed selection-metric schema on every evaluated stratum; schema drift fails closed instead of
    silently averaging a subset of windows. The report is discovery selection evidence only; it
    does not implement profitability or verification gates.
    """

    strata = tuple(expected_strata)
    if not strata or len(strata) != len(set(strata)):
        raise ValueError("expected_strata must be non-empty and unique")
    if not 0.0 < behavioral_similarity_threshold <= 1.0:
        raise ValueError("behavioral similarity threshold must be in (0, 1]")

    by_candidate: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for trial in trials:
        candidate_id = str(trial.get("candidate_id") or "").strip()
        fidelity = str(trial.get("fidelity") or "")
        if not candidate_id:
            raise ValueError("trial candidate_id is required")
        if not fidelity.startswith("d0-low-v1:"):
            continue
        by_candidate[candidate_id].append(trial)

    summaries: list[LowFidelityCandidateSummary] = []
    complete_behaviors: dict[str, BehavioralFingerprint] = {}
    expected_fidelities = {f"d0-low-v1:{item}" for item in strata}

    for candidate_id in sorted(by_candidate):
        rows = by_candidate[candidate_id]
        family_ids = {str(row.get("family_id") or "").strip() for row in rows}
        if len(family_ids) != 1 or "" in family_ids:
            raise ValueError("candidate trials must resolve to one family")
        family_id = next(iter(family_ids))
        fidelities = [str(row.get("fidelity")) for row in rows]
        if len(fidelities) != len(set(fidelities)):
            raise ValueError("candidate has duplicate low-fidelity stratum trials")
        terminal = all(str(row.get("status")) in {"evaluated", "rejected"} for row in rows)
        complete = terminal and set(fidelities) == expected_fidelities
        rejected = any(str(row.get("status")) == "rejected" for row in rows)

        selection_metrics: Sequence[Mapping[str, Any]] = ()
        behavior = None
        if complete and not rejected:
            selection_metrics = _validated_selection_metrics(rows)
            behavior = _combine_behaviors(rows)
            complete_behaviors[candidate_id] = behavior

        summaries.append(
            LowFidelityCandidateSummary(
                candidate_id=candidate_id,
                family_id=family_id,
                complete=complete,
                rejected=rejected,
                stratum_count=len(rows),
                mean_total_return=_mean_metric(selection_metrics, "total_return"),
                mean_expectancy=_mean_metric(selection_metrics, "expectancy"),
                total_trade_count=_sum_int_metric(selection_metrics, "trade_count"),
                mean_benchmark_relative_return=_mean_metric(
                    selection_metrics, "benchmark_relative_return"
                ),
                mean_max_drawdown=_mean_metric(selection_metrics, "max_drawdown"),
                mean_total_cost=_mean_metric(selection_metrics, "total_cost"),
                mean_exposure=_mean_metric(selection_metrics, "exposure"),
                mean_turnover=_mean_metric(
                    selection_metrics, "turnover_round_trips_per_1000_bars"
                ),
                behavior=behavior,
            )
        )

    representatives = select_behavioral_representatives(
        complete_behaviors,
        threshold=behavioral_similarity_threshold,
    )
    return LowFidelityDiscoveryReport(
        expected_strata=strata,
        candidates=tuple(summaries),
        representative_candidate_ids=representatives,
    )


def _validated_selection_metrics(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    validated: list[Mapping[str, Any]] = []
    for row in rows:
        metrics = row.get("metrics")
        if not isinstance(metrics, Mapping):
            raise ValueError("complete evaluated candidate is missing selection metrics")
        missing = [key for key in REQUIRED_SELECTION_METRICS if key not in metrics]
        if missing:
            raise ValueError(
                f"complete evaluated candidate is missing selection metrics: {missing}"
            )
        for key in REQUIRED_SELECTION_METRICS:
            value = metrics[key]
            if isinstance(value, bool):
                raise ValueError(f"selection metric {key} must be numeric")
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"selection metric {key} must be numeric") from exc
            if not math.isfinite(numeric):
                raise ValueError(f"selection metric {key} must be finite")
        trade_count = metrics["trade_count"]
        if int(float(trade_count)) != float(trade_count) or int(float(trade_count)) < 0:
            raise ValueError("selection metric trade_count must be a non-negative integer")
        validated.append(metrics)
    return tuple(validated)


def _combine_behaviors(rows: Sequence[Mapping[str, Any]]) -> BehavioralFingerprint:
    ordered = sorted(rows, key=lambda item: str(item.get("fidelity")))
    signal_keys: set[str] = set()
    trade_keys: set[str] = set()
    regime_returns: list[float] = []
    exposures: list[float] = []
    turnovers: list[float] = []
    for row in ordered:
        raw = row.get("behavior")
        if not isinstance(raw, Mapping):
            raise ValueError("complete evaluated candidate is missing behavioral fingerprint")
        signal_keys.update(str(value) for value in raw.get("signal_keys", ()))
        trade_keys.update(str(value) for value in raw.get("trade_keys", ()))
        regime_returns.extend(float(value) for value in raw.get("regime_returns", ()))
        exposures.append(float(raw.get("exposure_fraction")))
        turnovers.append(float(raw.get("turnover")))
    return BehavioralFingerprint(
        signal_keys=tuple(sorted(signal_keys)),
        trade_keys=tuple(sorted(trade_keys)),
        regime_returns=tuple(regime_returns),
        exposure_fraction=fmean(exposures),
        turnover=fmean(turnovers),
    )


def _mean_metric(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if key in row]
    return fmean(values) if values else None


def _sum_int_metric(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(int(row[key]) for row in rows if key in row)
