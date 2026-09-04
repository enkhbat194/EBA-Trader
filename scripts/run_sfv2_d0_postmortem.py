#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from eba_trader.strategy_factory_v2_postmortem import build_sfv2_d0_failure_postmortem


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o640)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the read-only Strategy Factory v2 D0 failure postmortem."
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--research-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--analysis-code-sha", required=True)
    args = parser.parse_args()

    payload = build_sfv2_d0_failure_postmortem(
        research_db_path=args.research_db,
        dataset_root=args.dataset_root,
    )
    payload["analysisCodeSha"] = args.analysis_code_sha.strip()
    payload["generatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    output = Path(args.output)
    _write_atomic(output, payload)

    summary = {
        "schema": payload["schema"],
        "authority": payload["authority"],
        "campaignId": payload["campaignId"],
        "analysisCodeSha": payload["analysisCodeSha"],
        "candidateCount": payload["candidateCount"],
        "familyCount": payload["familyCount"],
        "terminalTrialCount": payload["terminalTrialCount"],
        "survivorCount": payload["survivorCount"],
        "familyDiagnosisCounts": payload["familyDiagnosisCounts"],
        "failureFlagCounts": payload["failureFlagCounts"],
        "oneBarDelayDiagnostic": payload["oneBarDelayDiagnostic"],
        "output": str(output),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
