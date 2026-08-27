from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from .research_queue import ExperimentQueue
from .research_store import ResearchStore

ABLATION_STAGE = "m5_orderflow_ablation_dev"
MAX_ORDERFLOW_VARIANTS = 64


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(prefix: str, value: object, *, length: int = 20) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _positive_int(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer >= 1")
    return value


@dataclass(frozen=True, slots=True)
class OrderFlowGate:
    delta_ratio_threshold: float | None = None
    cvd_threshold: float | None = None
    stacked_imbalance_threshold: int | None = None

    def parameters(self) -> dict[str, float | int]:
        if (
            self.delta_ratio_threshold is None
            and self.cvd_threshold is None
            and self.stacked_imbalance_threshold is None
        ):
            raise ValueError(
                "order-flow gate requires delta_ratio_threshold, cvd_threshold, "
                "or stacked_imbalance_threshold"
            )
        result: dict[str, float | int] = {}
        if self.delta_ratio_threshold is not None:
            result["delta_ratio_threshold"] = _finite(
                self.delta_ratio_threshold,
                name="delta_ratio_threshold",
            )
        if self.cvd_threshold is not None:
            result["cvd_threshold"] = _finite(self.cvd_threshold, name="cvd_threshold")
        if self.stacked_imbalance_threshold is not None:
            result["stacked_imbalance_threshold"] = _positive_int(
                self.stacked_imbalance_threshold,
                name="stacked_imbalance_threshold",
            )
        return result

    @property
    def gate_id(self) -> str:
        return _fingerprint("gate", self.parameters(), length=16)


@dataclass(frozen=True, slots=True)
class AblationDefinition:
    dataset_ref: str
    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    fast_ema: int
    slow_ema: int
    initial_cash: float
    fee_bps: float
    slippage_bps: float
    gates: tuple[OrderFlowGate, ...]
    trade_start_time_ms: int | None = None
    max_attempts: int = 3

    def validate(self) -> None:
        if not self.dataset_ref.strip():
            raise ValueError("dataset_ref is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.interval.strip():
            raise ValueError("interval is required")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("dataset time range is invalid")
        if self.trade_start_time_ms is not None and not (
            self.start_ms <= self.trade_start_time_ms < self.end_ms
        ):
            raise ValueError("trade_start_time_ms must be inside the dataset window")
        if self.fast_ema < 1 or self.slow_ema < 2 or self.fast_ema >= self.slow_ema:
            raise ValueError("EMA parameters require 1 <= fast_ema < slow_ema")
        if _finite(self.initial_cash, name="initial_cash") <= 0:
            raise ValueError("initial_cash must be positive")
        if _finite(self.fee_bps, name="fee_bps") < 0:
            raise ValueError("fee_bps must be non-negative")
        if _finite(self.slippage_bps, name="slippage_bps") < 0:
            raise ValueError("slippage_bps must be non-negative")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if not self.gates:
            raise ValueError("at least one order-flow gate is required")
        if len(self.gates) > MAX_ORDERFLOW_VARIANTS:
            raise ValueError(
                f"order-flow ablation is capped at {MAX_ORDERFLOW_VARIANTS} variants"
            )
        gate_payloads = [_canonical_json(gate.parameters()) for gate in self.gates]
        if len(set(gate_payloads)) != len(gate_payloads):
            raise ValueError("duplicate order-flow gate variants are not allowed")

    def dataset_spec(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol.strip().upper(),
            "interval": self.interval.strip(),
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }

    def fixed_config(self) -> dict[str, Any]:
        fixed: dict[str, Any] = {
            "fast_ema": self.fast_ema,
            "slow_ema": self.slow_ema,
            "initial_cash": _finite(self.initial_cash, name="initial_cash"),
            "fee_bps": _finite(self.fee_bps, name="fee_bps"),
            "slippage_bps": _finite(self.slippage_bps, name="slippage_bps"),
        }
        if self.trade_start_time_ms is not None:
            fixed["trade_start_time_ms"] = self.trade_start_time_ms
        return fixed


@dataclass(frozen=True, slots=True)
class AblationPair:
    gate_id: str
    baseline_experiment_id: str
    orderflow_experiment_id: str
    orderflow_parameters: dict[str, float | int]


@dataclass(frozen=True, slots=True)
class EmittedAblationBatch:
    batch_id: str
    baseline_strategy_id: str
    orderflow_strategy_id: str
    baseline_experiment_id: str
    pairs: tuple[AblationPair, ...]

    @property
    def experiment_ids(self) -> tuple[str, ...]:
        return (
            self.baseline_experiment_id,
            *(pair.orderflow_experiment_id for pair in self.pairs),
        )


class M5OrderFlowAblationOrchestrator:
    """Emit controlled development experiments for candle-vs-order-flow ablations.

    The control and treatment arms intentionally share dataset identity, EMA parameters,
    capital, fees, slippage, trade-start semantics, queue retry policy and development
    stage. Only the allowlisted order-flow gate parameters differ. The worker remains
    hard-coded with ``allow_frozen_oos=False``; this orchestrator has no OOS authority.
    """

    def __init__(self, store: ResearchStore, queue: ExperimentQueue) -> None:
        self.store = store
        self.queue = queue

    def emit(self, definition: AblationDefinition) -> EmittedAblationBatch:
        definition.validate()
        dataset_ref = definition.dataset_ref.strip()
        dataset = definition.dataset_spec()
        fixed = definition.fixed_config()

        baseline_spec = {
            "adapter": "ema_feature_baseline_v1",
            "fixed": fixed,
            "dataset": dataset,
        }
        orderflow_spec = {
            "adapter": "ema_orderflow_v1",
            "fixed": fixed,
            "dataset": dataset,
        }
        baseline_strategy_id = self._strategy_id("BASE", baseline_spec)
        orderflow_strategy_id = self._strategy_id("OF", orderflow_spec)

        self.store.register_strategy_version(
            strategy_id=baseline_strategy_id,
            name="M5 order-flow ablation candle baseline",
            version=1,
            family="m5_orderflow_ablation_baseline",
            spec=baseline_spec,
        )
        self.store.register_strategy_version(
            strategy_id=orderflow_strategy_id,
            name="M5 order-flow ablation treatment",
            version=1,
            family="m5_orderflow_ablation_treatment",
            spec=orderflow_spec,
        )

        baseline_experiment_id = self.queue.enqueue(
            strategy_id=baseline_strategy_id,
            strategy_version=1,
            stage=ABLATION_STAGE,
            parameters={},
            dataset_ref=dataset_ref,
            max_attempts=definition.max_attempts,
        )

        ordered_gates = sorted(
            ((gate.gate_id, gate.parameters()) for gate in definition.gates),
            key=lambda item: item[0],
        )
        pairs = tuple(
            AblationPair(
                gate_id=gate_id,
                baseline_experiment_id=baseline_experiment_id,
                orderflow_experiment_id=self.queue.enqueue(
                    strategy_id=orderflow_strategy_id,
                    strategy_version=1,
                    stage=ABLATION_STAGE,
                    parameters=parameters,
                    dataset_ref=dataset_ref,
                    max_attempts=definition.max_attempts,
                ),
                orderflow_parameters=dict(parameters),
            )
            for gate_id, parameters in ordered_gates
        )

        batch_payload = {
            "schema": "m5_orderflow_ablation_batch_v1",
            "stage": ABLATION_STAGE,
            "dataset_ref": dataset_ref,
            "dataset": dataset,
            "fixed": fixed,
            "baseline_strategy_id": baseline_strategy_id,
            "orderflow_strategy_id": orderflow_strategy_id,
            "pairs": [
                {
                    "gate_id": pair.gate_id,
                    "baseline_experiment_id": pair.baseline_experiment_id,
                    "orderflow_experiment_id": pair.orderflow_experiment_id,
                    "orderflow_parameters": pair.orderflow_parameters,
                }
                for pair in pairs
            ],
        }
        return EmittedAblationBatch(
            batch_id=_fingerprint("abl", batch_payload, length=24),
            baseline_strategy_id=baseline_strategy_id,
            orderflow_strategy_id=orderflow_strategy_id,
            baseline_experiment_id=baseline_experiment_id,
            pairs=pairs,
        )

    @staticmethod
    def _strategy_id(arm: str, spec: dict[str, Any]) -> str:
        digest = hashlib.sha256(_canonical_json(spec).encode("utf-8")).hexdigest()[:18].upper()
        return f"M5-ABL-{arm}-{digest}"
