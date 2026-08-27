from __future__ import annotations

import argparse
import json
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
from .history import INTERVAL_MS, parse_utc
from .holdout_guard import assert_not_first_cycle_oos_overlap
from .orderflow_acquisition import (
    OrderFlowVenue,
    fetch_binance_agg_trades,
    repair_missing_id_ranges,
    write_acquisition_manifest,
)
from .orderflow_acquisition import (
    RequestJson as OrderFlowRequestJson,
)
from .orderflow_archive import ArchiveFetchBytes, fetch_binance_usdm_agg_trades_archive
from .orderflow_dataset import OrderFlowDatasetWriter, require_research_ready
from .orderflow_feature_dataset import materialize_orderflow_feature_dataset
from .research_evidence import canonical_json, sha256_text

WORKFLOW_SCHEMA = "m5_usdm_feature_build_v1"
ORDERFLOW_SOURCES = ("rest", "archive")


@dataclass(frozen=True, slots=True)
class M5FeatureBuildManifest:
    workflow_id: str
    schema: str
    symbol: str
    venue: str
    interval: str
    start_ms: int
    end_ms: int
    price_bucket: float
    candle_acquisition_id: str
    candle_manifest_path: str
    orderflow_dataset_id: str
    orderflow_manifest_path: str
    orderflow_acquisition_id: str
    orderflow_acquisition_path: str
    feature_dataset_id: str
    feature_manifest_path: str
    feature_csv_sha256: str
    dataset_ref: str

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "schema": self.schema,
            "symbol": self.symbol,
            "venue": self.venue,
            "interval": self.interval,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "price_bucket": self.price_bucket,
            "candle_acquisition_id": self.candle_acquisition_id,
            "candle_manifest_path": self.candle_manifest_path,
            "orderflow_dataset_id": self.orderflow_dataset_id,
            "orderflow_manifest_path": self.orderflow_manifest_path,
            "orderflow_acquisition_id": self.orderflow_acquisition_id,
            "orderflow_acquisition_path": self.orderflow_acquisition_path,
            "feature_dataset_id": self.feature_dataset_id,
            "feature_manifest_path": self.feature_manifest_path,
            "feature_csv_sha256": self.feature_csv_sha256,
            "dataset_ref": self.dataset_ref,
        }


def build_usdm_orderflow_feature_dataset(
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    price_bucket: float,
    dataset_root: str | Path,
    namespace: str = "m5_orderflow_dev",
    orderflow_source: str = "rest",
    candle_request_json: CandleRequestJson | None = None,
    orderflow_request_json: OrderFlowRequestJson | None = None,
    orderflow_archive_fetch_bytes: ArchiveFetchBytes | None = None,
) -> tuple[M5FeatureBuildManifest, Path]:
    symbol = symbol.strip().upper()
    namespace = namespace.strip()
    orderflow_source = orderflow_source.strip().lower()
    if not symbol:
        raise ValueError("symbol is required")
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    if not namespace or Path(namespace).is_absolute() or ".." in Path(namespace).parts:
        raise ValueError("namespace must be a safe relative path")
    if orderflow_source not in ORDERFLOW_SOURCES:
        raise ValueError(f"unsupported order-flow source: {orderflow_source}")
    if orderflow_source == "archive" and orderflow_request_json is not None:
        raise ValueError("REST request injection cannot be combined with archive order flow")
    if orderflow_source == "rest" and orderflow_archive_fetch_bytes is not None:
        raise ValueError("archive request injection requires archive order flow")
    if price_bucket <= 0:
        raise ValueError("price_bucket must be positive")
    step = INTERVAL_MS[interval]
    if start_ms < step or end_ms <= start_ms:
        raise ValueError("invalid feature dataset time range")
    if start_ms % step != 0 or end_ms % step != 0:
        raise ValueError("feature dataset range must align to interval boundaries")

    required_orderflow_start = start_ms - step
    assert_not_first_cycle_oos_overlap(
        symbol=symbol,
        interval=interval,
        start_ms=required_orderflow_start,
        end_ms=end_ms,
        context="M5 real USD-M feature dataset build",
    )

    dataset_root_path = Path(dataset_root)
    output_root = dataset_root_path / namespace
    candle_root = output_root / "candles"
    orderflow_root = output_root / "orderflow"
    feature_root = output_root / "features"
    workflow_root = output_root / "workflow"
    workflow_root.mkdir(parents=True, exist_ok=True)

    candles, candle_requests = fetch_binance_candles(
        symbol,
        interval,
        start_ms,
        end_ms,
        venue=CandleVenue.USD_M_FUTURES,
        request_json=candle_request_json,
    )
    candle_acquisition, candle_manifest_path = write_candle_acquisition(
        candle_root,
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        venue=CandleVenue.USD_M_FUTURES,
        candles=candles,
        requests=candle_requests,
    )
    verified_candles = load_candle_acquisition(candle_manifest_path)
    if verified_candles.venue != CandleVenue.USD_M_FUTURES.value:
        raise RuntimeError("real M5 feature workflow requires USD-M futures candles")

    if orderflow_source == "archive":
        orderflow_download = fetch_binance_usdm_agg_trades_archive(
            symbol,
            required_orderflow_start,
            end_ms,
            fetch_bytes=orderflow_archive_fetch_bytes,
        )
        dataset_source = "binance_usd_m_futures_aggTrades_public_archive"
    else:
        orderflow_download = fetch_binance_agg_trades(
            symbol,
            required_orderflow_start,
            end_ms,
            venue=OrderFlowVenue.USD_M_FUTURES,
            request_json=orderflow_request_json,
        )
        orderflow_download = repair_missing_id_ranges(
            orderflow_download,
            request_json=orderflow_request_json,
        )
        dataset_source = "binance_usd_m_futures_aggTrades_rest"

    orderflow_dataset = OrderFlowDatasetWriter(orderflow_root).write(
        symbol=symbol,
        payloads=orderflow_download.payloads,
        source=dataset_source,
    )
    require_research_ready(orderflow_dataset)
    orderflow_manifest_path = orderflow_root / f"{orderflow_dataset.dataset_id}.manifest.json"
    orderflow_acquisition, orderflow_acquisition_path = write_acquisition_manifest(
        orderflow_root,
        download=orderflow_download,
        dataset=orderflow_dataset,
    )
    if orderflow_acquisition.venue != OrderFlowVenue.USD_M_FUTURES.value:
        raise RuntimeError("real M5 feature workflow requires USD-M futures order flow")
    if verified_candles.symbol.upper() != orderflow_acquisition.symbol.upper():
        raise RuntimeError("candle and order-flow symbols do not match")

    feature = materialize_orderflow_feature_dataset(
        candle_path=verified_candles.csv_path,
        orderflow_manifest_path=orderflow_manifest_path,
        acquisition_manifest_path=orderflow_acquisition_path,
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        price_bucket=price_bucket,
        output_root=feature_root,
    )
    if feature.venue != CandleVenue.USD_M_FUTURES.value:
        raise RuntimeError("feature dataset venue is not USD-M futures")
    feature_manifest_path = feature_root / f"{feature.dataset_id}.manifest.json"
    feature_csv_path = Path(feature.feature_csv_path)
    resolved_dataset_root = dataset_root_path.resolve()
    try:
        dataset_ref = str(feature_csv_path.resolve().relative_to(resolved_dataset_root))
    except ValueError as exc:
        raise RuntimeError("feature dataset escaped configured dataset root") from exc

    identity = {
        "schema": WORKFLOW_SCHEMA,
        "symbol": symbol,
        "venue": OrderFlowVenue.USD_M_FUTURES.value,
        "interval": interval,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "price_bucket": price_bucket,
        "candle_acquisition_id": candle_acquisition.acquisition_id,
        "orderflow_dataset_id": orderflow_dataset.dataset_id,
        "orderflow_acquisition_id": orderflow_acquisition.acquisition_id,
        "feature_dataset_id": feature.dataset_id,
        "feature_csv_sha256": feature.feature_csv_sha256,
        "dataset_ref": dataset_ref,
    }
    workflow_id = f"m5ds_{sha256_text(canonical_json(identity))[:24]}"
    manifest = M5FeatureBuildManifest(
        workflow_id=workflow_id,
        schema=WORKFLOW_SCHEMA,
        symbol=symbol,
        venue=OrderFlowVenue.USD_M_FUTURES.value,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        price_bucket=price_bucket,
        candle_acquisition_id=candle_acquisition.acquisition_id,
        candle_manifest_path=str(candle_manifest_path),
        orderflow_dataset_id=orderflow_dataset.dataset_id,
        orderflow_manifest_path=str(orderflow_manifest_path),
        orderflow_acquisition_id=orderflow_acquisition.acquisition_id,
        orderflow_acquisition_path=str(orderflow_acquisition_path),
        feature_dataset_id=feature.dataset_id,
        feature_manifest_path=str(feature_manifest_path),
        feature_csv_sha256=feature.feature_csv_sha256,
        dataset_ref=dataset_ref,
    )
    path = workflow_root / f"{workflow_id}.manifest.json"
    text = canonical_json(manifest.as_dict())
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise RuntimeError("immutable M5 feature workflow manifest collision")
    path.write_text(text, encoding="utf-8")
    return manifest, path


def m5_build_orderflow_dataset_cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a verified BTCUSDT USD-M candle+order-flow development feature dataset"
        )
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1m", choices=sorted(INTERVAL_MS))
    parser.add_argument("--start", required=True, help="UTC ISO start")
    parser.add_argument("--end", required=True, help="Exclusive UTC ISO end")
    parser.add_argument("--price-bucket", type=float, default=1.0)
    parser.add_argument("--dataset-root", default="data/cache")
    parser.add_argument("--namespace", default="m5_orderflow_dev")
    parser.add_argument(
        "--orderflow-source",
        choices=ORDERFLOW_SOURCES,
        default="rest",
        help="REST for recent data; archive for reproducible historical Binance public data",
    )
    args = parser.parse_args()

    manifest, path = build_usdm_orderflow_feature_dataset(
        symbol=args.symbol,
        interval=args.interval,
        start_ms=parse_utc(args.start),
        end_ms=parse_utc(args.end),
        price_bucket=args.price_bucket,
        dataset_root=args.dataset_root,
        namespace=args.namespace,
        orderflow_source=args.orderflow_source,
    )
    print(
        json.dumps(
            {
                "workflow_id": manifest.workflow_id,
                "feature_dataset_id": manifest.feature_dataset_id,
                "dataset_ref": manifest.dataset_ref,
                "feature_csv_sha256": manifest.feature_csv_sha256,
                "manifest": str(path),
                "venue": manifest.venue,
                "orderflow_source": args.orderflow_source,
                "frozen_oos_opened": False,
                "live_execution_allowed": False,
            },
            sort_keys=True,
        )
    )
