from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .research_store import ResearchStore

EVIDENCE_SCHEMA = "eba-research-evidence-v1"


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_source_name(path: Path) -> str:
    resolved = path.resolve()
    src_root = Path(__file__).resolve().parent.parent
    try:
        return resolved.relative_to(src_root).as_posix()
    except ValueError:
        return resolved.name


def source_file_hashes(paths: Sequence[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        name = _stable_source_name(path)
        digest = sha256_file(path)
        previous = result.get(name)
        if previous is not None and previous != digest:
            raise ValueError(f"source provenance name collision: {name}")
        result[name] = digest
    return dict(sorted(result.items()))


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    evidence_id: str
    path: Path
    sha256: str


class ResearchEvidenceStore:
    """Immutable evidence manifests stored on disk and indexed in the research DB."""

    def __init__(self, store: ResearchStore, evidence_dir: str | Path) -> None:
        self.store = store
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with self.store._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    dataset_ref TEXT,
                    dataset_sha256 TEXT,
                    strategy_spec_sha256 TEXT NOT NULL,
                    source_commit TEXT NOT NULL,
                    adapter_name TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(experiment_id) REFERENCES experiment_runs(experiment_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_experiment
                    ON evidence_records(experiment_id, evidence_type, created_at);
                """
            )

    def persist_backtest_manifest(self, manifest: Mapping[str, Any]) -> EvidenceArtifact:
        if manifest.get("schema") != EVIDENCE_SCHEMA:
            raise ValueError(f"manifest.schema must be {EVIDENCE_SCHEMA!r}")
        experiment_id = str(manifest.get("experiment_id", "")).strip()
        if not experiment_id:
            raise ValueError("manifest experiment_id is required")

        strategy = manifest.get("strategy")
        dataset = manifest.get("dataset")
        adapter = manifest.get("adapter")
        source = manifest.get("source")
        if not isinstance(strategy, Mapping):
            raise ValueError("manifest strategy object is required")
        if not isinstance(dataset, Mapping):
            raise ValueError("manifest dataset object is required")
        if not isinstance(adapter, Mapping):
            raise ValueError("manifest adapter object is required")
        if not isinstance(source, Mapping):
            raise ValueError("manifest source object is required")

        manifest_json = canonical_json(manifest)
        artifact_sha256 = sha256_text(manifest_json)
        evidence_id = f"ev_{artifact_sha256[:24]}"
        record = {
            "evidence_id": evidence_id,
            "experiment_id": experiment_id,
            "evidence_type": "backtest",
            "artifact_sha256": artifact_sha256,
            "dataset_ref": str(dataset.get("ref", "")) or None,
            "dataset_sha256": str(dataset.get("sha256", "")) or None,
            "strategy_spec_sha256": str(strategy.get("spec_sha256", "")),
            "source_commit": str(source.get("git_commit", "")),
            "adapter_name": str(adapter.get("name", "")),
            "adapter_version": str(adapter.get("version", "")),
            "manifest_json": manifest_json,
        }
        for required in (
            "strategy_spec_sha256",
            "source_commit",
            "adapter_name",
            "adapter_version",
        ):
            if not record[required]:
                raise ValueError(f"manifest {required} is required")

        with self.store._connection() as connection:
            experiment = connection.execute(
                "SELECT 1 FROM experiment_runs WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if experiment is None:
                raise KeyError(f"unknown experiment for evidence: {experiment_id}")
            existing_record = connection.execute(
                "SELECT * FROM evidence_records WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            if (
                existing_record is not None
                and existing_record["artifact_sha256"] != artifact_sha256
            ):
                raise RuntimeError("immutable evidence DB collision")

        experiment_dir = self.evidence_dir / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        output = experiment_dir / f"{evidence_id}.json"
        if output.exists():
            existing_artifact = output.read_text(encoding="utf-8")
            if existing_artifact != manifest_json:
                raise RuntimeError("immutable evidence artifact collision")
        else:
            temporary = experiment_dir / f".{evidence_id}.{os.getpid()}.tmp"
            temporary.write_text(manifest_json, encoding="utf-8")
            temporary.replace(output)

        record["artifact_path"] = str(output)
        with self.store._connection() as connection:
            existing_record = connection.execute(
                "SELECT * FROM evidence_records WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            if existing_record is None:
                connection.execute(
                    """
                    INSERT INTO evidence_records(
                        evidence_id, experiment_id, evidence_type,
                        artifact_path, artifact_sha256, dataset_ref, dataset_sha256,
                        strategy_spec_sha256, source_commit, adapter_name,
                        adapter_version, manifest_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["evidence_id"],
                        record["experiment_id"],
                        record["evidence_type"],
                        record["artifact_path"],
                        record["artifact_sha256"],
                        record["dataset_ref"],
                        record["dataset_sha256"],
                        record["strategy_spec_sha256"],
                        record["source_commit"],
                        record["adapter_name"],
                        record["adapter_version"],
                        record["manifest_json"],
                    ),
                )
        return EvidenceArtifact(evidence_id=evidence_id, path=output, sha256=artifact_sha256)

    def list_for_experiment(self, experiment_id: str) -> list[dict[str, Any]]:
        with self.store._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM evidence_records
                WHERE experiment_id = ?
                ORDER BY created_at, evidence_id
                """,
                (experiment_id,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["manifest"] = json.loads(item.pop("manifest_json"))
            result.append(item)
        return result
