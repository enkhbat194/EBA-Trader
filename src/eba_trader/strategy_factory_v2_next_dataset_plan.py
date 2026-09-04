from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .history import INTERVAL_MS, parse_utc
from .orderflow_acquisition import OrderFlowVenue
from .strategy_factory_v2_next_catalog import EXPECTED_CATALOG_SHA256
from .strategy_factory_v2_next_design import EXPECTED_CAMPAIGN_ID
from .strategy_factory_v2_window_inventory import (
    HistoricalWindowInventory,
    assert_discovery_window_allowed,
    load_historical_window_inventory,
)

PLAN_SCHEMA = "sfv2_next_d0_dataset_plan_v1"
PLAN_AUTHORITY = "DATASET_PLAN_FREEZE_ONLY"
PLAN_PROVENANCE_CLASS = "D0_DISCOVERY_ONLY_NOT_CONFIRMATION"
EXPECTED_DESIGN_ID = "sfv2-next-existing-data-v1"
EXPECTED_SYMBOL = "BTCUSDT"
EXPECTED_VENUE = OrderFlowVenue.USD_M_FUTURES.value
EXPECTED_INTERVAL = "1m"
EXPECTED_PRICE_BUCKET = 5.0
EXPECTED_ORDERFLOW_SOURCE = "archive"
EXPECTED_NAMESPACE = "sfv2_next_d0_low_turnover_v1"
EXPECTED_REQUIRED_PRIOR_MINUTES = 1
EXPECTED_WINDOW_COUNT = 10
EXPECTED_WINDOWS = (
    ("next-d0-01", "2026-08-22T00:15:00Z", "2026-08-23T00:00:00Z"),
    ("next-d0-02", "2026-08-23T00:00:00Z", "2026-08-24T00:00:00Z"),
    ("next-d0-03", "2026-08-24T00:00:00Z", "2026-08-25T00:00:00Z"),
    ("next-d0-04", "2026-08-25T00:00:00Z", "2026-08-26T00:00:00Z"),
    ("next-d0-05", "2026-08-26T00:00:00Z", "2026-08-27T00:00:00Z"),
    ("next-d0-06", "2026-08-27T00:00:00Z", "2026-08-28T00:00:00Z"),
    ("next-d0-07", "2026-08-28T00:00:00Z", "2026-08-29T00:00:00Z"),
    ("next-d0-08", "2026-08-29T00:00:00Z", "2026-08-30T00:00:00Z"),
    ("next-d0-09", "2026-08-30T00:00:00Z", "2026-08-31T00:00:00Z"),
    ("next-d0-10", "2026-08-31T00:00:00Z", "2026-09-01T00:00:00Z"),
)


@dataclass(frozen=True, slots=True)
class NextD0Window:
    name: str
    start_ms: int
    end_ms: int

    @property
    def required_orderflow_start_ms(self) -> int:
        return self.start_ms - EXPECTED_REQUIRED_PRIOR_MINUTES * INTERVAL_MS[EXPECTED_INTERVAL]


@dataclass(frozen=True, slots=True)
class NextD0DatasetPlan:
    design_id: str
    campaign_id: str
    symbol: str
    venue: str
    interval: str
    price_bucket: float
    orderflow_source: str
    namespace: str
    catalog_sha256: str
    windows: tuple[NextD0Window, ...]
    authority: str = PLAN_AUTHORITY
    provenance_class: str = PLAN_PROVENANCE_CLASS
    performance_evaluation_allowed: bool = False
    dataset_receipt_frozen: bool = False


def _expected_windows() -> tuple[NextD0Window, ...]:
    return tuple(
        NextD0Window(name=name, start_ms=parse_utc(start), end_ms=parse_utc(end))
        for name, start, end in EXPECTED_WINDOWS
    )


def _validate_window_boundaries(
    windows: tuple[NextD0Window, ...],
    inventory: HistoricalWindowInventory,
) -> None:
    if windows != _expected_windows():
        raise ValueError("next D0 dataset windows changed from the frozen plan")
    step = INTERVAL_MS[EXPECTED_INTERVAL]
    for index, window in enumerate(windows):
        if window.start_ms >= window.end_ms:
            raise ValueError("next D0 window must have positive duration")
        if window.start_ms % step != 0 or window.end_ms % step != 0:
            raise ValueError("next D0 window must align to the 1m source interval")
        if window.start_ms % INTERVAL_MS["15m"] != 0:
            raise ValueError("next D0 window start must align to causal 15m aggregation")
        assert_discovery_window_allowed(
            inventory,
            start_ms=window.required_orderflow_start_ms,
            end_ms=window.end_ms,
            allow_inspected_reuse=True,
        )
        if index and windows[index - 1].end_ms != window.start_ms:
            raise ValueError("next D0 windows after the first must be contiguous")

    first = windows[0]
    if first.required_orderflow_start_ms < parse_utc("2026-08-22T00:00:00Z"):
        raise ValueError("first next D0 causal prior minute would enter sealed M5 OOS")
    if windows[-1].end_ms != parse_utc("2026-09-01T00:00:00Z"):
        raise ValueError("next D0 dataset must stop exactly at the SF4 protected boundary")


def load_next_d0_dataset_plan(
    path: str | Path,
    *,
    inventory_path: str | Path = "config/sfv2_historical_window_inventory_v1.json",
) -> NextD0DatasetPlan:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read next D0 dataset plan") from exc
    if not isinstance(payload, dict):
        raise ValueError("next D0 dataset plan must be an object")

    expected_fields = {
        "schema",
        "design_id",
        "campaign_id",
        "authority",
        "provenance_class",
        "symbol",
        "venue",
        "interval",
        "price_bucket",
        "orderflow_source",
        "namespace",
        "catalog_sha256",
        "required_prior_minutes",
        "windows",
        "materialization",
        "safety",
    }
    if set(payload) != expected_fields:
        raise ValueError("next D0 dataset plan fields changed")
    if payload["schema"] != PLAN_SCHEMA:
        raise ValueError("unsupported next D0 dataset plan schema")
    if payload["design_id"] != EXPECTED_DESIGN_ID:
        raise ValueError("next D0 dataset design identity changed")
    if payload["campaign_id"] != EXPECTED_CAMPAIGN_ID:
        raise ValueError("next D0 dataset campaign identity changed")
    if payload["authority"] != PLAN_AUTHORITY:
        raise ValueError("next D0 dataset plan cannot grant evaluation authority")
    if payload["provenance_class"] != PLAN_PROVENANCE_CLASS:
        raise ValueError("next D0 dataset provenance class changed")
    if payload["symbol"] != EXPECTED_SYMBOL:
        raise ValueError("next D0 dataset symbol changed")
    if payload["venue"] != EXPECTED_VENUE:
        raise ValueError("next D0 dataset venue changed")
    if payload["interval"] != EXPECTED_INTERVAL:
        raise ValueError("next D0 dataset interval changed")
    if payload["price_bucket"] != EXPECTED_PRICE_BUCKET:
        raise ValueError("next D0 dataset price bucket changed")
    if payload["orderflow_source"] != EXPECTED_ORDERFLOW_SOURCE:
        raise ValueError("next D0 dataset order-flow source changed")
    if payload["namespace"] != EXPECTED_NAMESPACE:
        raise ValueError("next D0 dataset namespace changed")
    if payload["catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise ValueError("next D0 dataset catalog binding changed")
    if payload["required_prior_minutes"] != EXPECTED_REQUIRED_PRIOR_MINUTES:
        raise ValueError("next D0 dataset causal prior-minute requirement changed")

    raw_windows = payload["windows"]
    if not isinstance(raw_windows, list) or len(raw_windows) != EXPECTED_WINDOW_COUNT:
        raise ValueError("next D0 dataset must contain exactly ten frozen windows")
    windows: list[NextD0Window] = []
    for row in raw_windows:
        if not isinstance(row, dict) or set(row) != {"name", "start", "end"}:
            raise ValueError("next D0 dataset window fields changed")
        windows.append(
            NextD0Window(
                name=str(row["name"]),
                start_ms=parse_utc(str(row["start"])),
                end_ms=parse_utc(str(row["end"])),
            )
        )

    materialization = payload["materialization"]
    expected_materialization = {
        "required": True,
        "exact_feature_sha_per_window_required": True,
        "exact_workflow_manifest_per_window_required": True,
        "dataset_receipt_frozen": False,
        "performance_evaluation_allowed": False,
    }
    if materialization != expected_materialization:
        raise ValueError("next D0 dataset materialization boundary changed")

    safety = payload["safety"]
    expected_safety = {
        "fresh_confirmation_evidence": False,
        "verification_authority": False,
        "d1_opened": False,
        "frozen_oos_opened": False,
        "sf4_data_access_allowed": False,
        "demo_promotion_allowed": False,
        "live_execution_allowed": False,
        "real_execution_allowed": False,
    }
    if safety != expected_safety:
        raise ValueError("next D0 dataset safety boundary changed")

    inventory = load_historical_window_inventory(inventory_path)
    frozen_windows = tuple(windows)
    _validate_window_boundaries(frozen_windows, inventory)
    return NextD0DatasetPlan(
        design_id=EXPECTED_DESIGN_ID,
        campaign_id=EXPECTED_CAMPAIGN_ID,
        symbol=EXPECTED_SYMBOL,
        venue=EXPECTED_VENUE,
        interval=EXPECTED_INTERVAL,
        price_bucket=EXPECTED_PRICE_BUCKET,
        orderflow_source=EXPECTED_ORDERFLOW_SOURCE,
        namespace=EXPECTED_NAMESPACE,
        catalog_sha256=EXPECTED_CATALOG_SHA256,
        windows=frozen_windows,
    )
