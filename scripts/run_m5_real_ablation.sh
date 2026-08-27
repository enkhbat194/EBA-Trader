#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/Eba-Trader"
RESEARCH_ROOT="/var/lib/eba-trader/research"
DATASET_ROOT="$RESEARCH_ROOT/datasets"
RESEARCH_DB="$RESEARCH_ROOT/eba_research.db"
EVIDENCE_ROOT="$RESEARCH_ROOT/evidence"
GATES_JSON="$REPO_DIR/config/m5_orderflow_gate_set_v1.json"
LOCK_FILE="$RESEARCH_ROOT/m5-real-ablation.lock"
SYMBOL="BTCUSDT"
INTERVAL="1m"
PRICE_BUCKET="1.0"
FAST_EMA="12"
SLOW_EMA="26"
INITIAL_CASH="10000"
FEE_BPS="4.0"
SLIPPAGE_BPS="1.5"
START=""
END=""
RESULT_JSON=""

usage() {
  cat <<'EOF'
Usage: run_m5_real_ablation.sh --start <UTC ISO> --end <UTC ISO> [options]

Required:
  --start <UTC ISO>      Development window start, e.g. 2026-08-01T00:00:00Z
  --end <UTC ISO>        Exclusive end, e.g. 2026-08-02T00:00:00Z

Options:
  --symbol <symbol>      Default BTCUSDT
  --interval <interval>  Default 1m
  --price-bucket <n>     Default 1.0
  --fast-ema <n>         Default 12
  --slow-ema <n>         Default 26
  --initial-cash <n>     Default 10000
  --fee-bps <n>          Default 4.0
  --slippage-bps <n>     Default 1.5
  --gates-json <path>    Default config/m5_orderflow_gate_set_v1.json
  --result-json <path>   Write immutable sanitized comparison report after workers finish
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START="$2"; shift 2 ;;
    --end) END="$2"; shift 2 ;;
    --symbol) SYMBOL="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --price-bucket) PRICE_BUCKET="$2"; shift 2 ;;
    --fast-ema) FAST_EMA="$2"; shift 2 ;;
    --slow-ema) SLOW_EMA="$2"; shift 2 ;;
    --initial-cash) INITIAL_CASH="$2"; shift 2 ;;
    --fee-bps) FEE_BPS="$2"; shift 2 ;;
    --slippage-bps) SLIPPAGE_BPS="$2"; shift 2 ;;
    --gates-json) GATES_JSON="$2"; shift 2 ;;
    --result-json) RESULT_JSON="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$START" || -z "$END" ]]; then
  usage >&2
  exit 2
fi
if [[ $EUID -ne 0 ]]; then
  echo "Run as root on the Linode runtime." >&2
  exit 1
fi
if [[ ! -x "$REPO_DIR/.venv/bin/eba-build-orderflow-features" ]]; then
  echo "EBA Trader virtualenv/CLI is not installed." >&2
  exit 1
fi
if [[ ! -f "$GATES_JSON" ]]; then
  echo "Gate policy not found: $GATES_JSON" >&2
  exit 1
fi

mkdir -p "$DATASET_ROOT" "$EVIDENCE_ROOT"
chmod 750 "$RESEARCH_ROOT" "$DATASET_ROOT" "$EVIDENCE_ROOT"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another M5 real ablation run is already active." >&2
  exit 3
fi

cd "$REPO_DIR"
echo "EBA_M5_STAGE=dataset_build" >&2
BUILD_JSON="$($REPO_DIR/.venv/bin/eba-build-orderflow-features \
  --symbol "$SYMBOL" \
  --interval "$INTERVAL" \
  --start "$START" \
  --end "$END" \
  --price-bucket "$PRICE_BUCKET" \
  --dataset-root "$DATASET_ROOT" \
  --namespace m5_orderflow_dev \
  --orderflow-source archive)"

WORKFLOW_MANIFEST="$(BUILD_JSON="$BUILD_JSON" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BUILD_JSON"])
print(payload["manifest"])
PY
)"

echo "$BUILD_JSON"

echo "EBA_M5_STAGE=queue_emit" >&2
QUEUE_JSON="$($REPO_DIR/.venv/bin/eba-m5-real-ablation \
  --workflow-manifest "$WORKFLOW_MANIFEST" \
  --gates-json "$GATES_JSON" \
  --dataset-root "$DATASET_ROOT" \
  --db "$RESEARCH_DB" \
  --fast-ema "$FAST_EMA" \
  --slow-ema "$SLOW_EMA" \
  --initial-cash "$INITIAL_CASH" \
  --fee-bps "$FEE_BPS" \
  --slippage-bps "$SLIPPAGE_BPS")"

echo "$QUEUE_JSON"

EXPERIMENT_COUNT="$(QUEUE_JSON="$QUEUE_JSON" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["QUEUE_JSON"])
print(len(payload["experiment_ids"]))
PY
)"

echo "EBA_M5_STAGE=worker" >&2
$REPO_DIR/.venv/bin/eba-research-worker \
  --db "$RESEARCH_DB" \
  --dataset-root "$DATASET_ROOT" \
  --evidence-dir "$EVIDENCE_ROOT" \
  --stage m5_orderflow_ablation_dev \
  --max-jobs "$EXPERIMENT_COUNT" \
  --lease-seconds 900 \
  --retry-delay-seconds 60

if [[ -n "$RESULT_JSON" ]]; then
  echo "EBA_M5_STAGE=report" >&2
  mkdir -p "$(dirname "$RESULT_JSON")"
  $REPO_DIR/.venv/bin/python -m eba_trader.m5_ablation_report \
    --db "$RESEARCH_DB" \
    --batch-json "$QUEUE_JSON" \
    --output "$RESULT_JSON"
fi

echo "EBA_M5_STAGE=complete" >&2
echo "M5 real development ablation run complete."
echo "Research DB: $RESEARCH_DB"
echo "Evidence root: $EVIDENCE_ROOT"
if [[ -n "$RESULT_JSON" ]]; then
  echo "Comparison report: $RESULT_JSON"
fi
echo "Frozen OOS was not opened; real execution remains locked."
