from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from eba_trader.m5_corpus_materializer import materialize_m5_development_corpus
from eba_trader.m5_dataset_workflow import WORKFLOW_SCHEMA, M5FeatureBuildManifest
from eba_trader.m5_study_policy import (
    DEFAULT_M5_DEVELOPMENT_CORPUS,
    DEFAULT_M5_STUDY_POLICY,
)
from eba_trader.orderflow_acquisition import USDM_AGG_TRADES_URL
from eba_trader.orderflow_archive import USDM_DAILY_AGG_TRADES_ROOT
from eba_trader.research_evidence import canonical_json, sha256_file


def _fake_builder(
    calls: list[int],
    *,
    fail_after: int | None = None,
    endpoint_for: Callable[[str], str] | None = None,
):
    def build_window(**kwargs):
        start_ms = int(kwargs["start_ms"])
        end_ms = int(kwargs["end_ms"])
        if fail_after is not None and len(calls) >= fail_after:
            raise RuntimeError("synthetic interrupted corpus build")
        calls.append(start_ms)

        dataset_root = Path(kwargs["dataset_root"])
        namespace = str(kwargs["namespace"])
        source = str(kwargs["orderflow_source"])
        price_bucket = float(kwargs["price_bucket"])
        token = str(start_ms)

        feature_dir = dataset_root / namespace / "features"
        orderflow_dir = dataset_root / namespace / "orderflow"
        workflow_dir = dataset_root / namespace / "workflow"
        feature_dir.mkdir(parents=True, exist_ok=True)
        orderflow_dir.mkdir(parents=True, exist_ok=True)
        workflow_dir.mkdir(parents=True, exist_ok=True)

        feature_path = feature_dir / f"feature-{token}.csv"
        feature_path.write_text(
            f"open_time_ms,close\n{start_ms},50000\n",
            encoding="utf-8",
        )
        feature_sha = sha256_file(feature_path)
        dataset_ref = str(feature_path.relative_to(dataset_root))

        endpoint = (
            endpoint_for(source)
            if endpoint_for is not None
            else (USDM_DAILY_AGG_TRADES_ROOT if source == "archive" else USDM_AGG_TRADES_URL)
        )
        acquisition_path = orderflow_dir / f"acq-{token}.json"
        acquisition_path.write_text(
            canonical_json(
                {
                    "acquisition_id": f"acq-{token}",
                    "dataset_id": f"ofd-{token}",
                    "symbol": DEFAULT_M5_STUDY_POLICY.symbol,
                    "venue": DEFAULT_M5_STUDY_POLICY.venue,
                    "endpoint": endpoint,
                    "requested_start_ms": start_ms - 60_000,
                    "requested_end_ms": end_ms,
                    "record_count": 1,
                    "first_trade_id": 1,
                    "last_trade_id": 1,
                    "request_count": 1,
                    "requests_sha256": "a" * 64,
                }
            ),
            encoding="utf-8",
        )

        workflow_id = f"workflow-{token}"
        manifest = M5FeatureBuildManifest(
            workflow_id=workflow_id,
            schema=WORKFLOW_SCHEMA,
            study_policy_id=DEFAULT_M5_STUDY_POLICY.policy_id,
            study_phase="development",
            symbol=DEFAULT_M5_STUDY_POLICY.symbol,
            venue=DEFAULT_M5_STUDY_POLICY.venue,
            interval=DEFAULT_M5_STUDY_POLICY.interval,
            start_ms=start_ms,
            end_ms=end_ms,
            price_bucket=price_bucket,
            candle_acquisition_id=f"candle-{token}",
            candle_manifest_path=str(dataset_root / namespace / "candles" / f"{token}.json"),
            orderflow_dataset_id=f"ofd-{token}",
            orderflow_manifest_path=str(orderflow_dir / f"ofd-{token}.manifest.json"),
            orderflow_acquisition_id=f"acq-{token}",
            orderflow_acquisition_path=str(acquisition_path),
            feature_dataset_id=f"feature-{token}",
            feature_manifest_path=str(feature_path.with_suffix(".manifest.json")),
            feature_csv_sha256=feature_sha,
            dataset_ref=dataset_ref,
        )
        workflow_path = workflow_dir / f"{workflow_id}.manifest.json"
        workflow_path.write_text(canonical_json(manifest.as_dict()), encoding="utf-8")
        return manifest, workflow_path

    return build_window


def test_materializer_builds_all_pre_registered_windows_and_replays_without_network(
    tmp_path: Path,
) -> None:
    calls: list[int] = []
    first, first_path = materialize_m5_development_corpus(
        dataset_root=tmp_path,
        build_window=_fake_builder(calls),
    )

    assert len(calls) == len(DEFAULT_M5_DEVELOPMENT_CORPUS.windows) == 12
    assert len(first.windows) == 12
    assert first.policy_id == DEFAULT_M5_STUDY_POLICY.policy_id
    assert first.corpus_id == DEFAULT_M5_DEVELOPMENT_CORPUS.corpus_id
    assert first.orderflow_source == "archive"
    assert first_path.is_file()

    replay_calls: list[int] = []
    second, second_path = materialize_m5_development_corpus(
        dataset_root=tmp_path,
        build_window=_fake_builder(replay_calls, fail_after=0),
    )

    assert replay_calls == []
    assert second == first
    assert second_path == first_path


def test_materializer_resumes_from_immutable_per_window_checkpoints(tmp_path: Path) -> None:
    first_calls: list[int] = []
    with pytest.raises(RuntimeError, match="synthetic interrupted"):
        materialize_m5_development_corpus(
            dataset_root=tmp_path,
            build_window=_fake_builder(first_calls, fail_after=3),
        )
    assert len(first_calls) == 3

    checkpoint_dir = next((tmp_path / "m5_orderflow_dev" / "corpus" / "checkpoints").iterdir())
    assert len(list(checkpoint_dir.glob("*.json"))) == 3

    resume_calls: list[int] = []
    materialization, _ = materialize_m5_development_corpus(
        dataset_root=tmp_path,
        build_window=_fake_builder(resume_calls),
    )

    assert len(resume_calls) == 9
    assert len(materialization.windows) == 12


def test_materializer_detects_feature_tampering_before_replay(tmp_path: Path) -> None:
    materialization, _ = materialize_m5_development_corpus(
        dataset_root=tmp_path,
        build_window=_fake_builder([]),
    )
    first = materialization.windows[0]
    feature_path = tmp_path / first.dataset_ref
    feature_path.write_text(feature_path.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")

    replay_calls: list[int] = []
    with pytest.raises(RuntimeError, match="feature CSV integrity mismatch"):
        materialize_m5_development_corpus(
            dataset_root=tmp_path,
            build_window=_fake_builder(replay_calls, fail_after=0),
        )
    assert replay_calls == []


def test_materializer_rejects_wrong_orderflow_source_provenance(tmp_path: Path) -> None:
    def wrong_endpoint(_: str) -> str:
        return USDM_AGG_TRADES_URL

    with pytest.raises(RuntimeError, match="source provenance mismatch"):
        materialize_m5_development_corpus(
            dataset_root=tmp_path,
            orderflow_source="archive",
            build_window=_fake_builder([], endpoint_for=wrong_endpoint),
        )


def test_materializer_manifest_is_complete_and_keeps_locked_domains_closed(tmp_path: Path) -> None:
    materialization, manifest_path = materialize_m5_development_corpus(
        dataset_root=tmp_path,
        build_window=_fake_builder([]),
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["window_count"] == 12
    assert payload["frozen_oos_opened"] is False
    assert payload["m5_frozen_oos_opened"] is False
    assert payload["live_execution_allowed"] is False
    assert [item["window_name"] for item in payload["windows"]] == [
        window.name for window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows
    ]
    assert [item["start_ms"] for item in payload["windows"]] == [
        window.start_ms for window in DEFAULT_M5_DEVELOPMENT_CORPUS.windows
    ]
    assert materialization.materialization_id.startswith("m5corpusmat_")


@pytest.mark.parametrize("namespace", ["", "../escape", "/absolute"])
def test_materializer_rejects_unsafe_namespace(tmp_path: Path, namespace: str) -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        materialize_m5_development_corpus(
            dataset_root=tmp_path,
            namespace=namespace,
            build_window=_fake_builder([]),
        )
