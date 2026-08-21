from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist, mean, median, stdev
from typing import Any

import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .derivatives_audit import (
    DerivativeKline,
    FundingRecord,
    _load_funding_csv,
    _load_kline_csv,
)
from .history import Candle, load_csv, parse_utc
from .m7_funding_flow import prepare_futures_features
from .m13_ml_policy import (
    BASE_ROUND_TRIP_COST_BPS,
    BTC_FUNDING_SHA256,
    BTC_FUTURES_SHA256,
    BTC_SPOT_CHALLENGE_SHA256,
    BTC_SPOT_RESEARCH_SHA256,
    CHALLENGE_YEAR,
    DISCOVERY_PREDICTION_YEARS,
    ETH_FUTURES_SHA256,
    FDR_Q_THRESHOLD,
    FEATURE_COUNT,
    FEATURE_NAMES,
    HORIZONS_BARS,
    MIN_CHALLENGE_EVENTS,
    MIN_CHALLENGE_PROFIT_FACTOR,
    MIN_DISCOVERY_DAYS,
    MIN_DISCOVERY_EVENTS,
    MIN_DISCOVERY_EVENTS_PER_YEAR,
    MIN_DISCOVERY_PROFIT_FACTOR,
    MIN_POSITIVE_CHALLENGE_MONTHS,
    MODEL_FAMILIES,
    PROBABILITY_GATES,
    RANDOM_STATE,
    SEVERE_ROUND_TRIP_COST_BPS,
    sha256_file,
    verify_m13_freeze,
)
from .provenance import collect_source_provenance

STEP_MS = 15 * 60 * 1000
HOUR_MS = 60 * 60 * 1000
FUNDING_MEAN_RECORDS = 90


@dataclass(frozen=True, slots=True)
class MLSample:
    signal_time_ms: int
    year: int
    features: tuple[float | None, ...]
    gross_returns: dict[int, float]


@dataclass(frozen=True, slots=True)
class SelectedEvent:
    signal_time_ms: int
    year: int
    probability: float
    gross_return: float
    base_net_return: float
    severe_net_return: float


@dataclass(frozen=True, slots=True)
class YearStats:
    year: int
    event_count: int
    mean_base_net: float | None
    mean_severe_net: float | None


@dataclass(frozen=True, slots=True)
class EvaluationStats:
    event_count: int
    distinct_days: int
    mean_gross: float | None
    mean_base_net: float | None
    mean_severe_net: float | None
    median_base_net: float | None
    profit_factor_base: float | None
    win_rate_base: float | None
    daily_mean_p_value: float
    fdr_q_value: float
    positive_months: int
    yearly: tuple[YearStats, ...]
    discovery_pass: bool
    challenge_pass: bool
    status: str


@dataclass(frozen=True, slots=True)
class ConfigResult:
    name: str
    model_family: str
    probability_gate: float
    horizon_bars: int
    discovery: EvaluationStats
    challenge: EvaluationStats | None
    classification: str


def _is_contiguous(left_time: int, right_time: int, steps: int = 1) -> bool:
    return right_time - left_time == steps * STEP_MS


def _spot_return(bars: tuple[Candle, ...], index: int, lookback: int) -> float | None:
    if index < lookback:
        return None
    first = bars[index - lookback]
    last = bars[index]
    if not _is_contiguous(first.open_time_ms, last.open_time_ms, lookback):
        return None
    return last.close / first.close - 1.0


def _derivative_return(
    bars: tuple[DerivativeKline, ...],
    index: int,
    lookback: int,
) -> float | None:
    if index < lookback:
        return None
    first = bars[index - lookback]
    last = bars[index]
    if not _is_contiguous(first.open_time_ms, last.open_time_ms, lookback):
        return None
    return last.close / first.close - 1.0


def _spot_abs_return_mean_4h(bars: tuple[Candle, ...], index: int) -> float | None:
    if index < 16:
        return None
    if not _is_contiguous(bars[index - 16].open_time_ms, bars[index].open_time_ms, 16):
        return None
    values = [
        abs(bars[position].close / bars[position - 1].close - 1.0)
        for position in range(index - 15, index + 1)
    ]
    return mean(values)


def _spot_prior_96(bars: tuple[Candle, ...], index: int) -> tuple[float | None, float | None]:
    if index < 96:
        return None, None
    first = bars[index - 96]
    previous = bars[index - 1]
    if not _is_contiguous(first.open_time_ms, previous.open_time_ms, 95):
        return None, None
    window = bars[index - 96 : index]
    median_volume = median(item.volume for item in window)
    volume_ratio = bars[index].volume / median_volume if median_volume > 0 else None
    weighted = sum(
        ((item.high + item.low + item.close) / 3.0) * item.volume for item in window
    )
    total_volume = sum(item.volume for item in window)
    if total_volume <= 0:
        return volume_ratio, None
    vwap = weighted / total_volume
    return volume_ratio, bars[index].close / vwap - 1.0


def _latest_funding_features(
    funding: tuple[FundingRecord, ...],
    funding_times: tuple[int, ...],
    signal_close_time_ms: int,
) -> tuple[float | None, float | None]:
    position = bisect_right(funding_times, signal_close_time_ms) - 1
    if position < 0:
        return None, None
    latest = funding[position].funding_rate
    if position + 1 < FUNDING_MEAN_RECORDS:
        return latest, None
    trailing = funding[position - FUNDING_MEAN_RECORDS + 1 : position + 1]
    return latest, latest - mean(item.funding_rate for item in trailing)


def _outcome(
    spot: tuple[Candle, ...],
    signal_index: int,
    horizon: int,
) -> float | None:
    entry_index = signal_index + 1
    exit_index = signal_index + horizon
    if exit_index >= len(spot):
        return None
    signal = spot[signal_index]
    entry = spot[entry_index]
    exit_bar = spot[exit_index]
    if not _is_contiguous(signal.open_time_ms, entry.open_time_ms):
        return None
    if not _is_contiguous(signal.open_time_ms, exit_bar.open_time_ms, horizon):
        return None
    return exit_bar.close / entry.open - 1.0


def build_samples(
    spot: tuple[Candle, ...],
    btc_futures: tuple[DerivativeKline, ...],
    funding: tuple[FundingRecord, ...],
    eth_futures: tuple[DerivativeKline, ...],
) -> tuple[MLSample, ...]:
    btc_index = {item.open_time_ms: index for index, item in enumerate(btc_futures)}
    eth_index = {item.open_time_ms: index for index, item in enumerate(eth_futures)}
    funding_times = tuple(item.funding_time_ms for item in funding)

    btc_flow = prepare_futures_features(btc_futures)
    eth_flow = prepare_futures_features(eth_futures)

    samples: list[MLSample] = []
    for spot_index, spot_bar in enumerate(spot):
        if spot_bar.open_time_ms % HOUR_MS != 0:
            continue
        btc_position = btc_index.get(spot_bar.open_time_ms)
        eth_position = eth_index.get(spot_bar.open_time_ms)
        if btc_position is None or eth_position is None:
            continue

        btc_ret_1h = _spot_return(spot, spot_index, 4)
        btc_ret_4h = _spot_return(spot, spot_index, 16)
        btc_ret_12h = _spot_return(spot, spot_index, 48)
        abs_ret_4h = _spot_abs_return_mean_4h(spot, spot_index)
        spot_volume_ratio, spot_vwap_disp = _spot_prior_96(spot, spot_index)

        btc_perp_ret_1h = _derivative_return(btc_futures, btc_position, 4)
        btc_flow_1h = btc_flow.flow_1h[btc_position]
        btc_perp = btc_futures[btc_position]
        btc_premium = btc_perp.close / spot_bar.close - 1.0

        funding_latest, funding_delta = _latest_funding_features(
            funding,
            funding_times,
            spot_bar.close_time_ms,
        )

        eth_ret_1h = _derivative_return(eth_futures, eth_position, 4)
        eth_ret_4h = _derivative_return(eth_futures, eth_position, 16)
        eth_ret_12h = _derivative_return(eth_futures, eth_position, 48)
        eth_flow_1h = eth_flow.flow_1h[eth_position]

        relative_1h = (
            eth_ret_1h - btc_ret_1h
            if eth_ret_1h is not None and btc_ret_1h is not None
            else None
        )
        relative_4h = (
            eth_ret_4h - btc_ret_4h
            if eth_ret_4h is not None and btc_ret_4h is not None
            else None
        )

        features = (
            btc_ret_1h,
            btc_ret_4h,
            btc_ret_12h,
            abs_ret_4h,
            spot_volume_ratio,
            spot_vwap_disp,
            btc_perp_ret_1h,
            btc_flow_1h.taker_buy_share if btc_flow_1h is not None else None,
            btc_flow_1h.quote_volume_intensity if btc_flow_1h is not None else None,
            btc_premium,
            funding_latest,
            funding_delta,
            eth_ret_1h,
            eth_ret_4h,
            eth_ret_12h,
            eth_flow_1h.taker_buy_share if eth_flow_1h is not None else None,
            eth_flow_1h.quote_volume_intensity if eth_flow_1h is not None else None,
            relative_1h,
            relative_4h,
        )
        if len(features) != FEATURE_COUNT:
            raise RuntimeError("M13 feature vector length changed after freeze")

        gross_returns = {
            horizon: value
            for horizon in HORIZONS_BARS
            if (value := _outcome(spot, spot_index, horizon)) is not None
        }
        if not gross_returns:
            continue

        year = datetime.fromtimestamp(spot_bar.open_time_ms / 1000.0, tz=UTC).year
        samples.append(
            MLSample(
                signal_time_ms=spot_bar.open_time_ms,
                year=year,
                features=features,
                gross_returns=gross_returns,
            )
        )
    return tuple(samples)


def _model(model_family: str) -> Pipeline:
    if model_family == "logistic":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=1.0,
                        class_weight="balanced",
                        max_iter=1000,
                        solver="lbfgs",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        )
    if model_family == "hist_gb":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_iter=200,
                        learning_rate=0.05,
                        max_depth=3,
                        l2_regularization=1.0,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unknown frozen M13 model family: {model_family}")


def _matrix(samples: list[MLSample]) -> list[list[float]]:
    return [
        [math.nan if value is None else float(value) for value in sample.features]
        for sample in samples
    ]


def _labels(samples: list[MLSample], horizon: int) -> list[int]:
    threshold = BASE_ROUND_TRIP_COST_BPS / 10_000.0
    return [int(sample.gross_returns[horizon] > threshold) for sample in samples]


def _eligible(samples: tuple[MLSample, ...], years: set[int], horizon: int) -> list[MLSample]:
    return [
        sample
        for sample in samples
        if sample.year in years and horizon in sample.gross_returns
    ]


def _fit_predict(
    model_family: str,
    train: list[MLSample],
    predict: list[MLSample],
    horizon: int,
) -> list[float]:
    if not train or not predict:
        return []
    labels = _labels(train, horizon)
    if len(set(labels)) < 2:
        raise RuntimeError(
            f"M13 {model_family} horizon {horizon} training fold has only one target class"
        )
    estimator = _model(model_family)
    estimator.fit(_matrix(train), labels)
    probabilities = estimator.predict_proba(_matrix(predict))[:, 1]
    return [float(value) for value in probabilities]


def walk_forward_predictions(
    samples: tuple[MLSample, ...],
    model_family: str,
    horizon: int,
) -> tuple[tuple[MLSample, float], ...]:
    predictions: list[tuple[MLSample, float]] = []
    folds = (
        ({2021}, {2022}),
        ({2021, 2022}, {2023}),
    )
    for train_years, predict_years in folds:
        train = _eligible(samples, train_years, horizon)
        predict = _eligible(samples, predict_years, horizon)
        probabilities = _fit_predict(model_family, train, predict, horizon)
        predictions.extend(zip(predict, probabilities, strict=True))
    predictions.sort(key=lambda item: item[0].signal_time_ms)
    return tuple(predictions)


def challenge_predictions(
    samples: tuple[MLSample, ...],
    model_family: str,
    horizon: int,
) -> tuple[tuple[MLSample, float], ...]:
    train = _eligible(samples, {2021, 2022, 2023}, horizon)
    predict = _eligible(samples, {CHALLENGE_YEAR}, horizon)
    probabilities = _fit_predict(model_family, train, predict, horizon)
    return tuple(zip(predict, probabilities, strict=True))


def selected_events(
    predictions: tuple[tuple[MLSample, float], ...],
    *,
    horizon: int,
    probability_gate: float,
) -> tuple[SelectedEvent, ...]:
    base_cost = BASE_ROUND_TRIP_COST_BPS / 10_000.0
    severe_cost = SEVERE_ROUND_TRIP_COST_BPS / 10_000.0
    result: list[SelectedEvent] = []
    for sample, probability in predictions:
        if probability < probability_gate:
            continue
        gross = sample.gross_returns[horizon]
        result.append(
            SelectedEvent(
                signal_time_ms=sample.signal_time_ms,
                year=sample.year,
                probability=probability,
                gross_return=gross,
                base_net_return=gross - base_cost,
                severe_net_return=gross - severe_cost,
            )
        )
    return tuple(result)


def _utc_day(timestamp_ms: int):
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).date()


def _utc_month(timestamp_ms: int) -> int:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).month


def _daily_p_value(events: tuple[SelectedEvent, ...]) -> tuple[int, float]:
    grouped: dict[object, list[float]] = defaultdict(list)
    for event in events:
        grouped[_utc_day(event.signal_time_ms)].append(event.base_net_return)
    daily_means = [mean(values) for values in grouped.values()]
    if len(daily_means) < 2:
        return len(daily_means), 1.0
    average = mean(daily_means)
    sample_std = stdev(daily_means)
    if sample_std == 0:
        return len(daily_means), 0.0 if average > 0 else 1.0
    z_score = average / (sample_std / math.sqrt(len(daily_means)))
    p_value = 1.0 - NormalDist().cdf(z_score)
    return len(daily_means), min(max(p_value, 0.0), 1.0)


def benjamini_hochberg(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    total = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for reverse_index in range(total - 1, -1, -1):
        key, p_value = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, p_value * total / rank)
        adjusted[key] = min(max(running, 0.0), 1.0)
    return adjusted


def _profit_factor(values: list[float]) -> float | None:
    if not values:
        return None
    positive = sum(value for value in values if value > 0)
    negative = -sum(value for value in values if value < 0)
    if negative == 0:
        return math.inf if positive > 0 else None
    return positive / negative


def summarize_events(
    events: tuple[SelectedEvent, ...],
    *,
    q_value: float = 1.0,
    discovery: bool,
    status: str = "MEASURED",
) -> EvaluationStats:
    distinct_days, p_value = _daily_p_value(events)
    base = [item.base_net_return for item in events]
    severe = [item.severe_net_return for item in events]
    gross = [item.gross_return for item in events]
    years = DISCOVERY_PREDICTION_YEARS if discovery else (CHALLENGE_YEAR,)
    yearly = tuple(
        YearStats(
            year=year,
            event_count=len(selected := [item for item in events if item.year == year]),
            mean_base_net=mean(item.base_net_return for item in selected) if selected else None,
            mean_severe_net=(
                mean(item.severe_net_return for item in selected) if selected else None
            ),
        )
        for year in years
    )
    monthly: dict[int, list[float]] = defaultdict(list)
    for item in events:
        monthly[_utc_month(item.signal_time_ms)].append(item.base_net_return)
    positive_months = sum(mean(values) > 0 for values in monthly.values())
    return EvaluationStats(
        event_count=len(events),
        distinct_days=distinct_days,
        mean_gross=mean(gross) if gross else None,
        mean_base_net=mean(base) if base else None,
        mean_severe_net=mean(severe) if severe else None,
        median_base_net=median(base) if base else None,
        profit_factor_base=_profit_factor(base),
        win_rate_base=sum(value > 0 for value in base) / len(base) if base else None,
        daily_mean_p_value=p_value,
        fdr_q_value=q_value,
        positive_months=positive_months,
        yearly=yearly,
        discovery_pass=False,
        challenge_pass=False,
        status=status,
    )


def _passes_discovery(stats: EvaluationStats) -> bool:
    if stats.event_count < MIN_DISCOVERY_EVENTS or stats.distinct_days < MIN_DISCOVERY_DAYS:
        return False
    if stats.mean_base_net is None or stats.mean_base_net <= 0:
        return False
    if stats.mean_severe_net is None or stats.mean_severe_net <= 0:
        return False
    if stats.median_base_net is None or stats.median_base_net <= 0:
        return False
    if (
        stats.profit_factor_base is None
        or stats.profit_factor_base <= MIN_DISCOVERY_PROFIT_FACTOR
    ):
        return False
    if stats.fdr_q_value > FDR_Q_THRESHOLD:
        return False
    by_year = {item.year: item for item in stats.yearly}
    for year in DISCOVERY_PREDICTION_YEARS:
        item = by_year.get(year)
        if (
            item is None
            or item.event_count < MIN_DISCOVERY_EVENTS_PER_YEAR
            or item.mean_base_net is None
            or item.mean_base_net <= 0
        ):
            return False
    return True


def _passes_challenge(stats: EvaluationStats) -> bool:
    return (
        stats.event_count >= MIN_CHALLENGE_EVENTS
        and stats.mean_base_net is not None
        and stats.mean_base_net > 0
        and stats.mean_severe_net is not None
        and stats.mean_severe_net > 0
        and stats.median_base_net is not None
        and stats.median_base_net > 0
        and stats.profit_factor_base is not None
        and stats.profit_factor_base > MIN_CHALLENGE_PROFIT_FACTOR
        and stats.positive_months >= MIN_POSITIVE_CHALLENGE_MONTHS
    )


def _config_name(model_family: str, gate: float, horizon: int) -> str:
    return f"{model_family}_p{int(round(gate * 100))}_h{horizon}"


def evaluate_configs(samples: tuple[MLSample, ...]) -> tuple[ConfigResult, ...]:
    preliminary: dict[str, EvaluationStats] = {}
    p_values: dict[str, float] = {}
    metadata: dict[str, tuple[str, float, int]] = {}

    prediction_cache: dict[tuple[str, int], tuple[tuple[MLSample, float], ...]] = {}
    for model_family in MODEL_FAMILIES:
        for horizon in HORIZONS_BARS:
            prediction_cache[(model_family, horizon)] = walk_forward_predictions(
                samples,
                model_family,
                horizon,
            )

    for model_family in MODEL_FAMILIES:
        for gate in PROBABILITY_GATES:
            for horizon in HORIZONS_BARS:
                name = _config_name(model_family, gate, horizon)
                events = selected_events(
                    prediction_cache[(model_family, horizon)],
                    horizon=horizon,
                    probability_gate=gate,
                )
                stats = summarize_events(events, discovery=True)
                preliminary[name] = stats
                p_values[name] = stats.daily_mean_p_value
                metadata[name] = (model_family, gate, horizon)

    q_values = benjamini_hochberg(p_values)
    discovery_stats: dict[str, EvaluationStats] = {}
    for name, stats in preliminary.items():
        with_q = replace(stats, fdr_q_value=q_values[name])
        discovery_stats[name] = replace(with_q, discovery_pass=_passes_discovery(with_q))

    results: list[ConfigResult] = []
    challenge_cache: dict[tuple[str, int], tuple[tuple[MLSample, float], ...]] = {}
    for name in sorted(metadata):
        model_family, gate, horizon = metadata[name]
        discovery = discovery_stats[name]
        challenge: EvaluationStats | None = None
        classification = "OBSERVATION_ONLY"
        if discovery.discovery_pass:
            cache_key = (model_family, horizon)
            if cache_key not in challenge_cache:
                challenge_cache[cache_key] = challenge_predictions(
                    samples,
                    model_family,
                    horizon,
                )
            events = selected_events(
                challenge_cache[cache_key],
                horizon=horizon,
                probability_gate=gate,
            )
            measured = summarize_events(events, discovery=False)
            challenge = replace(measured, challenge_pass=_passes_challenge(measured))
            if challenge.challenge_pass:
                classification = "ML_LONG_EDGE_CANDIDATE"
        results.append(
            ConfigResult(
                name=name,
                model_family=model_family,
                probability_gate=gate,
                horizon_bars=horizon,
                discovery=discovery,
                challenge=challenge,
                classification=classification,
            )
        )
    return tuple(results)


def _verify_input_hashes(
    *,
    spot_research_path: Path,
    spot_challenge_path: Path,
    btc_futures_path: Path,
    funding_path: Path,
    eth_futures_path: Path,
) -> dict[str, str]:
    expected = {
        "btc_spot_research": (spot_research_path, BTC_SPOT_RESEARCH_SHA256),
        "btc_spot_challenge": (spot_challenge_path, BTC_SPOT_CHALLENGE_SHA256),
        "btc_futures": (btc_futures_path, BTC_FUTURES_SHA256),
        "btc_funding": (funding_path, BTC_FUNDING_SHA256),
        "eth_futures": (eth_futures_path, ETH_FUTURES_SHA256),
    }
    actual: dict[str, str] = {}
    for name, (path, frozen_hash) in expected.items():
        if not path.is_file():
            raise FileNotFoundError(f"M13 frozen input missing: {path}")
        digest = sha256_file(path)
        if digest != frozen_hash:
            raise RuntimeError(f"M13 frozen input hash mismatch for {name}: {digest}")
        actual[name] = digest
    return actual


def run_m13_ml_edge(
    *,
    spot_research_path: str | Path = "data/cache/m2/btcusdt_15m_research.csv",
    spot_challenge_path: str | Path = "data/cache/m2/btcusdt_15m_validation.csv",
    btc_futures_path: str | Path = "data/cache/m6/btcusdt_usdm_perpetual_15m_2021_2024.csv",
    funding_path: str | Path = "data/cache/m6/btcusdt_usdm_funding_2021_2024.csv",
    eth_futures_path: str | Path = "data/cache/m13/m11_ethusdt_usdm_15m_normalized.csv",
    report_path: str | Path = "artifacts/m13_ml_edge_engine.json",
) -> dict[str, Any]:
    report_output = Path(report_path)
    if report_output.exists():
        raise RuntimeError("M13 evidence already exists; preserve the first complete result")

    freeze = verify_m13_freeze()
    provenance = collect_source_provenance(require_clean=True)
    paths = {
        "spot_research_path": Path(spot_research_path),
        "spot_challenge_path": Path(spot_challenge_path),
        "btc_futures_path": Path(btc_futures_path),
        "funding_path": Path(funding_path),
        "eth_futures_path": Path(eth_futures_path),
    }
    hashes = _verify_input_hashes(**paths)

    spot_research = tuple(load_csv(paths["spot_research_path"]))
    spot_challenge = tuple(load_csv(paths["spot_challenge_path"]))
    spot = tuple(sorted((*spot_research, *spot_challenge), key=lambda item: item.open_time_ms))
    btc_futures = tuple(_load_kline_csv(paths["btc_futures_path"]))
    funding = tuple(_load_funding_csv(paths["funding_path"]))
    eth_futures = tuple(_load_kline_csv(paths["eth_futures_path"]))

    if not spot or not btc_futures or not funding or not eth_futures:
        raise RuntimeError("M13 frozen inputs must be non-empty")
    if max(item.open_time_ms for item in spot) >= parse_utc("2025-01-01T00:00:00Z"):
        raise RuntimeError("M13 must not access 2025 BTC Spot OOS")
    if max(item.open_time_ms for item in eth_futures) >= parse_utc("2025-01-01T00:00:00Z"):
        raise RuntimeError("M13 must not access 2025 ETH OOS")

    samples = build_samples(spot, btc_futures, funding, eth_futures)
    allowed_years = {2021, 2022, 2023, 2024}
    if any(sample.year not in allowed_years for sample in samples):
        raise RuntimeError("M13 sample escaped the frozen 2021-2024 development window")

    results = evaluate_configs(samples)
    candidates = [item.name for item in results if item.classification == "ML_LONG_EDGE_CANDIDATE"]
    decision = "ML_EDGE_CANDIDATE_FOUND" if candidates else "NO_STABLE_ML_EDGE_FOUND"

    report: dict[str, Any] = {
        "phase": "m13_ml_edge_engine_first_complete_frozen_evidence",
        "decision": decision,
        "policy_freeze": freeze,
        "source_provenance": provenance,
        "software": {
            "sklearn_version": sklearn.__version__,
            "random_state": RANDOM_STATE,
        },
        "input_sha256": hashes,
        "feature_names": list(FEATURE_NAMES),
        "sample_counts_by_year": {
            str(year): sum(sample.year == year for sample in samples)
            for year in (2021, 2022, 2023, 2024)
        },
        "search": {
            "configuration_count": len(results),
            "ml_long_edge_candidates": candidates,
            "discovery_passing_configs": sum(item.discovery.discovery_pass for item in results),
            "challenge_passing_configs": sum(
                bool(item.challenge and item.challenge.challenge_pass) for item in results
            ),
            "results": [asdict(item) for item in results],
        },
        "oos_2025": "LOCKED_NOT_ACCESSED",
        "risk_sizing": "BLOCKED_RESEARCH_ONLY",
        "live_execution": "BLOCKED_RESEARCH_ONLY",
        "parameter_changes_after_result": "FORBIDDEN",
    }
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen M13 supervised-ML edge research")
    parser.add_argument("--report", default="artifacts/m13_ml_edge_engine.json")
    parser.add_argument(
        "--eth-futures",
        default="data/cache/m13/m11_ethusdt_usdm_15m_normalized.csv",
    )
    args = parser.parse_args()
    report = run_m13_ml_edge(
        report_path=args.report,
        eth_futures_path=args.eth_futures,
    )
    print("M13 decision:", report["decision"])
    print("ML_LONG_EDGE_CANDIDATE:", report["search"]["ml_long_edge_candidates"])
    print("discovery_passing_configs:", report["search"]["discovery_passing_configs"])
    print("challenge_passing_configs:", report["search"]["challenge_passing_configs"])
    print("2025 OOS remains", report["oos_2025"])


if __name__ == "__main__":
    main()
