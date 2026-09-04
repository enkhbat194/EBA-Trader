from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .candle_acquisition import (
    CandleVenue,
    fetch_binance_candles,
    load_candle_acquisition,
    write_candle_acquisition,
)
from .candle_acquisition import (
    RequestJson as CandleRequestJson,
)
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .orderflow_acquisition import OrderFlowVenue, write_acquisition_manifest
from .orderflow_archive import ArchiveFetchBytes, fetch_binance_usdm_agg_trades_archive
from .orderflow_dataset import OrderFlowDatasetWriter, require_research_ready
from .orderflow_feature_dataset import (
    load_orderflow_feature_csv,
    materialize_orderflow_feature_dataset,
)
from .research_evidence import canonical_json, sha256_file, sha256_text
from .strategy_factory_v2_next_dataset_plan import (
    NextD0DatasetPlan,
    NextD0Window,
    load_next_d0_dataset_plan,
)
from .strategy_factory_v2_window_inventory import (
    assert_discovery_window_allowed,
    load_historical_window_inventory,
)

WORKFLOW_SCHEMA = "sfv2_next_d0_usdm_feature_build_v1"
WORKFLOW_AUTHORITY = "D0_DATA_MATERIALIZATION_ONLY"
STUDY_PHASE = "d0_discovery_not_confirmation"
DEFAULT_PLAN_PATH = Path("config/sfv2_next_d0_dataset_plan_v1.json")
DEFAULT_INVENTORY_PATH = Path("config/sfv2_historical_window_inventory_v1.json")


@dataclass(frozen=True, slots=True)
class NextD0FeatureBuildManifest:
    workflow_id: str
    window_name: str
    schema: str
    authority: str
    study_phase: str
    design_id: str
    campaign_id: str
    catalog_sha256: str
    dataset_plan_sha256: str
    symbol: str
    venue: str
    interval: str
    start_ms: int
    end_ms: int
    required_orderflow_start_ms: int
    price_bucket: float
    orderflow_source: str
    candle_acquisition_id: str
    candle_manifest_ref: str
    orderflow_dataset_id: str
    orderflow_manifest_ref: str
    orderflow_acquisition_id: str
    orderflow_acquisition_ref: str
    feature_dataset_id: str
    feature_manifest_ref: str
    feature_csv_sha256: str
    dataset_ref: str
    row_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "window_name": self.window_name,
            "schema": self.schema,
            "authority": self.authority,
            "study_phase": self.study_phase,
            "design_id": self.design_id,
            "campaign_id": self.campaign_id,
            "catalog_sha256": self.catalog_sha256,
            "dataset_plan_sha256": self.dataset_plan_sha256,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "required_orderflow_start_ms": self.required_orderflow_start_ms,
            "price_bucket": self.price_bucket,
            "orderflow_source": self.orderflow_source,
            "candle_acquisition_id": self.candle_acquisition_id,
            "candle_manifest_ref": self.candle_manifest_ref,
            "orderflow_dataset_id": self.orderflow_dataset_id,
            "orderflow_manifest_ref": self.orderflow_manifest_ref,
            "orderflow_acquisition_id": self.orderflow_acquisition_id,
            "orderflow_acquisition_ref": self.orderflow_acquisition_ref,
            "feature_dataset_id": self.feature_dataset_id,
            "feature_manifest_ref": self.feature_manifest_ref,
            "feature_csv_sha256": self.feature_csv_sha256,
            "dataset_ref": self.dataset_ref,
            "row_count": self.row_count,
            "fresh_confirmation_evidence": False,
            "verification_authority": False,
            "d1_opened": False,
            "frozen_oos_opened": False,
            "sf4_data_accessed": False,
            "live_execution_allowed": False,
            "real_execution_allowed": False,
        }


def _safe_ref(root: Path, value: str | Path, *, label: str) -> str:
    resolved_root = root.resolve()
    resolved = Path(value).resolve()
    try:
        return str(resolved.relative_to(resolved_root))
    except ValueError as exc:
        raise RuntimeError(f"{label} escaped configured dataset root") from exc


def _find_window(plan: NextD0DatasetPlan, window_name: str) -> NextD0Window:
    matches = [window for window in plan.windows if window.name == window_name]
    if len(matches) != 1:
        raise ValueError("window_name must identify exactly one frozen next D0 window")
    return matches[0]


def build_next_d0_window_feature_dataset(
    *,
    window_name: str,
    dataset_root: str | Path,
    plan_path: str | Path = DEFAULT_PLAN_PATH,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
    candle_request_json: CandleRequestJson | None = None,
    orderflow_archive_fetch_bytes: ArchiveFetchBytes | None = None,
) -> tuple[NextD0FeatureBuildManifest, Path]:
    plan_path = Path(plan_path)
    inventory_path = Path(inventory_path)
    plan = load_next_d0_dataset_plan(plan_path, inventory_path=inventory_path)
    window = _find_window(plan, window_name.strip())
    inventory = load_historical_window_inventory(inventory_path)

    assert_not_first_cycle_oos_overlap(
        symbol=plan.symbol,
        interval=plan.interval,
        start_ms=window.required_orderflow_start_ms,
        end_ms=window.end_ms,
        context="SFv2 next D0 feature materialization",
    )
    assert_discovery_window_allowed(
        inventory,
        start_ms=window.required_orderflow_start_ms,
        end_ms=window.end_ms,
        allow_inspected_reuse=True,
    )

    root = Path(dataset_root)
    output_root = root / plan.namespace
    candle_root = output_root / "candles"
    orderflow_root = output_root / "orderflow"
    feature_root = output_root / "features"
    workflow_root = output_root / "workflow"
    workflow_root.mkdir(parents=True, exist_ok=True)

    candles, candle_requests = fetch_binance_candles(
        plan.symbol,
        plan.interval,
        window.start_ms,
        window.end_ms,
        venue=CandleVenue.USD_M_FUTURES,
        request_json=candle_request_json,
    )
    candle_acquisition, candle_manifest_path = write_candle_acquisition(
        candle_root,
        symbol=plan.symbol,
        interval=plan.interval,
        start_ms=window.start_ms,
        end_ms=window.end_ms,
        venue=CandleVenue.USD_M_FUTURES,
        candles=candles,
        requests=candle_requests,
    )
    verified_candles = load_candle_acquisition(candle_manifest_path)
    if verified_candles.venue != CandleVenue.USD_M_FUTURES.value:
        raise RuntimeError("next D0 workflow requires USD-M futures candles")

    orderflow_download = fetch_binance_usdm_agg_trades_archive(
        plan.symbol,
        window.required_orderflow_start_ms,
        window.end_ms,
        fetch_bytes=orderflow_archive_fetch_bytes,
    )
    orderflow_dataset = OrderFlowDatasetWriter(orderflow_root).write(
        symbol=plan.symbol,
        payloads=orderflow_download.payloads,
        source="binance_usd_m_futures_aggTrades_public_archive",
    )
    require_research_ready(orderflow_dataset)
    orderflow_manifest_path = orderflow_root / f"{orderflow_dataset.dataset_id}.manifest.json"
    orderflow_acquisition, orderflow_acquisition_path = write_acquisition_manifest(
        orderflow_root,
        download=orderflow_download,
        dataset=orderflow_dataset,
    )
    if orderflow_acquisition.venue != OrderFlowVenue.USD_M_FUTURES.value:
        raise RuntimeError("next D0 workflow requires USD-M futures order flow")
    if verified_candles.symbol.upper() != orderflow_acquisition.symbol.upper():
        raise RuntimeError("next D0 candle and order-flow symbols do not match")

    feature = materialize_orderflow_feature_dataset(
        candle_path=verified_candles.csv_path,
        orderflow_manifest_path=orderflow_manifest_path,
        acquisition_manifest_path=orderflow_acquisition_path,
        symbol=plan.symbol,
        interval=plan.interval,
        start_ms=window.start_ms,
        end_ms=window.end_ms,
        price_bucket=plan.price_bucket,
        output_root=feature_root,
    )
    if feature.venue != CandleVenue.USD_M_FUTURES.value:
        raise RuntimeError("next D0 feature dataset venue is not USD-M futures")
    feature_path = Path(feature.feature_csv_path)
    rows = load_orderflow_feature_csv(feature_path)
    expected_rows = (window.end_ms - window.start_ms) // 60_000
    if len(rows) != expected_rows or feature.row_count != expected_rows:
        raise RuntimeError("next D0 feature row count does not cover the frozen window")
    if rows[0].candle.open_time_ms != window.start_ms:
        raise RuntimeError("next D0 feature dataset starts outside the frozen window")
    if rows[-1].candle.open_time_ms != window.end_ms - 60_000:
        raise RuntimeError("next D0 feature dataset ends outside the frozen window")

    feature_manifest_path = feature_root / f"{feature.dataset_id}.manifest.json"
    dataset_plan_sha256 = sha256_file(plan_path)
    dataset_ref = _safe_ref(root, feature_path, label="feature dataset")
    identity = {
        "schema": WORKFLOW_SCHEMA,
        "authority": WORKFLOW_AUTHORITY,
        "study_phase": STUDY_PHASE,
        "window_name": window.name,
        "design_id": plan.design_id,
        "campaign_id": plan.campaign_id,
        "catalog_sha256": plan.catalog_sha256,
        "dataset_plan_sha256": dataset_plan_sha256,
        "symbol": plan.symbol,
        "venue": plan.venue,
        "interval": plan.interval,
        "start_ms": window.start_ms,
        "end_ms": window.end_ms,
        "required_orderflow_start_ms": window.required_orderflow_start_ms,
        "price_bucket": plan.price_bucket,
        "orderflow_source": plan.orderflow_source,
        "candle_acquisition_id": candle_acquisition.acquisition_id,
        "orderflow_dataset_id": orderflow_dataset.dataset_id,
        "orderflow_acquisition_id": orderflow_acquisition.acquisition_id,
        "feature_dataset_id": feature.dataset_id,
        "feature_csv_sha256": feature.feature_csv_sha256,
        "dataset_ref": dataset_ref,
        "row_count": len(rows),
    }
    workflow_id = f"sfv2nd0_{sha256_text(canonical_json(identity))[:24]}"
    manifest = NextD0FeatureBuildManifest(
        workflow_id=workflow_id,
        window_name=window.name,
        schema=WORKFLOW_SCHEMA,
        authority=WORKFLOW_AUTHORITY,
        study_phase=STUDY_PHASE,
        design_id=plan.design_id,
        campaign_id=plan.campaign_id,
        catalog_sha256=plan.catalog_sha256,
        dataset_plan_sha256=dataset_plan_sha256,
        symbol=plan.symbol,
        venue=plan.venue,
        interval=plan.interval,
        start_ms=window.start_ms,
        end_ms=window.end_ms,
        required_orderflow_start_ms=window.required_orderflow_start_ms,
        price_bucket=plan.price_bucket,
        orderflow_source=plan.orderflow_source,
        candle_acquisition_id=candle_acquisition.acquisition_id,
        candle_manifest_ref=_safe_ref(root, candle_manifest_path, label="candle manifest"),
        orderflow_dataset_id=orderflow_dataset.dataset_id,
        orderflow_manifest_ref=_safe_ref(
            root,
            orderflow_manifest_path,
            label="order-flow manifest",
        ),
        orderflow_acquisition_id=orderflow_acquisition.acquisition_id,
        orderflow_acquisition_ref=_safe_ref(
            root,
            orderflow_acquisition_path,
            label="order-flow acquisition",
        ),
        feature_dataset_id=feature.dataset_id,
        feature_manifest_ref=_safe_ref(
            root,
            feature_manifest_path,
            label="feature manifest",
        ),
        feature_csv_sha256=feature.feature_csv_sha256,
        dataset_ref=dataset_ref,
        row_count=len(rows),
    )
    path = workflow_root / f"{workflow_id}.manifest.json"
    text = canonical_json(manifest.as_dict())
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise RuntimeError("immutable next D0 workflow manifest collision")
    path.write_text(text, encoding="utf-8")
    return manifest, path
