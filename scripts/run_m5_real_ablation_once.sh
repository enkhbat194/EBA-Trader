#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
RESEARCH_ROOT="/var/lib/eba-trader/research"
EVIDENCE_ROOT="$RESEARCH_ROOT/evidence"
PROOF_FILE="$RESEARCH_ROOT/m5-real-ablation-latest.json"
RUN_LOCK="$RESEARCH_ROOT/m5-real-ablation-once.lock"
START="2026-08-01T00:00:00Z"
END="2026-08-01T04:00:00Z"
WINDOW_ID="20260801T000000Z-20260801T040000Z"
REPORT_FILE="$EVIDENCE_ROOT/m5-real-ablation-$WINDOW_ID.json"
LOG_FILE="$RESEARCH_ROOT/m5-real-ablation-$WINDOW_ID.log"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root on the Linode runtime." >&2
  exit 1
fi

mkdir -p "$RESEARCH_ROOT" "$EVIDENCE_ROOT"
chmod 750 "$RESEARCH_ROOT" "$EVIDENCE_ROOT"
exec 8>"$RUN_LOCK"
if ! flock -n 8; then
  exit 0
fi

write_marker() {
  local phase="$1"
  local exit_code="${2:-0}"
  PHASE="$phase" EXIT_CODE="$exit_code" PROOF_FILE="$PROOF_FILE" REPORT_FILE="$REPORT_FILE" \
    LOG_FILE="$LOG_FILE" START="$START" END="$END" WINDOW_ID="$WINDOW_ID" \
    "$REPO_DIR/.venv/bin/python" - <<'PY'
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

phase = os.environ["PHASE"]
report_path = Path(os.environ["REPORT_FILE"])
log_path = Path(os.environ["LOG_FILE"])
payload = {
    "schema": "m5_real_ablation_autorun_v1",
    "phase": phase,
    "updatedAt": datetime.now(tz=UTC).isoformat(),
    "windowId": os.environ["WINDOW_ID"],
    "start": os.environ["START"],
    "end": os.environ["END"],
    "reportPath": str(report_path),
    "edgeClaimAllowed": False,
    "promotionAuthority": False,
    "frozenOosOpened": False,
    "liveExecutionAllowed": False,
}
if phase == "FAILED":
    payload["exitCode"] = int(os.environ["EXIT_CODE"])
    if log_path.is_file():
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
        except OSError:
            text = ""
        stages = re.findall(r"EBA_M5_STAGE=([a-z_]+)", text)
        if stages:
            payload["failureStage"] = stages[-1]
        text = re.sub(r"EBA_M5_STAGE=[a-z_]+", " ", text)
        text = re.sub(
            r"(?i)(api[_-]?(?:key|secret)|authorization|bearer|token|password|signature)"
            r"(\s*[:=]\s*)([^\s,;]+)",
            r"\1\2[REDACTED]",
            text,
        )
        text = re.sub(
            r"(?i)([?&](?:signature|apiKey|token|secret)=)[^&\s]+",
            r"\1[REDACTED]",
            text,
        )
        summary = " ".join(text.split())[-1600:]
        if summary:
            payload["errorSummary"] = summary
if report_path.is_file():
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report = None
    if isinstance(report, dict):
        payload.update(
            {
                "batchId": report.get("batchId"),
                "workflowId": report.get("workflowId"),
                "treatmentCount": report.get("treatmentCount"),
                "allTerminal": bool(report.get("allTerminal")),
                "allExperimentsPassed": bool(report.get("allExperimentsPassed")),
                "evidenceComplete": bool(report.get("evidenceComplete")),
                "edgeClaimAllowed": False,
                "promotionAuthority": False,
            }
        )
output = Path(os.environ["PROOF_FILE"])
with tempfile.NamedTemporaryFile(
    mode="w",
    encoding="utf-8",
    dir=output.parent,
    prefix=f".{output.name}.",
    delete=False,
) as handle:
    json.dump(payload, handle, sort_keys=True, indent=2)
    handle.write("\n")
    temp = Path(handle.name)
temp.chmod(0o640)
temp.replace(output)
PY
}

if [[ -f "$REPORT_FILE" ]]; then
  if REPORT_FILE="$REPORT_FILE" "$REPO_DIR/.venv/bin/python" - <<'PY'
import json
import os
from pathlib import Path

report = json.loads(Path(os.environ["REPORT_FILE"]).read_text(encoding="utf-8"))
raise SystemExit(
    0
    if report.get("allTerminal") is True
    and report.get("evidenceComplete") is True
    and report.get("frozenOosOpened") is False
    and report.get("liveExecutionAllowed") is False
    else 1
)
PY
  then
    write_marker COMPLETE 0
    exit 0
  fi
fi

write_marker RUNNING 0
set +e
bash "$REPO_DIR/scripts/run_m5_real_ablation.sh" \
  --start "$START" \
  --end "$END" \
  --result-json "$REPORT_FILE" >"$LOG_FILE" 2>&1
code=$?
set -e

if [[ $code -ne 0 ]]; then
  write_marker FAILED "$code"
  exit "$code"
fi

write_marker COMPLETE 0
