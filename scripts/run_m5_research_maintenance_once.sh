#!/usr/bin/env bash
set -uo pipefail

cd /opt/Eba-Trader

ablation_exit=0
corpus_exit=0
multiwindow_exit=0
qualification_exit=0
robustness_exit=0
demo_exit=0
qualification_state="deferred"
robustness_state="deferred"

/bin/bash /opt/Eba-Trader/scripts/run_m5_real_ablation_once.sh || ablation_exit=$?
/opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_corpus_runtime || corpus_exit=$?

if [[ $corpus_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_multiwindow_runtime || multiwindow_exit=$?
else
  multiwindow_exit=1
fi

if [[ $multiwindow_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_candidate_qualification_runtime || qualification_exit=$?
else
  qualification_exit=1
fi

if [[ $qualification_exit -eq 0 ]]; then
  qualification_summary="$(/opt/Eba-Trader/.venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path('/var/lib/eba-trader/research/m5-robustness-qualification-latest.json')
payload = json.loads(path.read_text(encoding='utf-8'))
if payload.get('phase') != 'COMPLETE' or payload.get('complete') is not True or payload.get('safe') is not True:
    raise SystemExit('qualification status is not safely complete')
count = payload.get('eligibleCandidateCount')
top = payload.get('topEligibleCandidate')
if isinstance(count, bool) or not isinstance(count, int) or count < 0:
    raise SystemExit('invalid eligibleCandidateCount')
if count == 0 and top is not None:
    raise SystemExit('zero eligible candidates cannot have a top candidate')
if count > 0 and (not isinstance(top, str) or not top):
    raise SystemExit('eligible candidates require a top candidate')
print(f"{count}\t{top or '-'}")
PY
)" || qualification_exit=$?
fi

if [[ $qualification_exit -eq 0 ]]; then
  IFS=$'\t' read -r eligible_count top_candidate <<< "$qualification_summary"
  if [[ "$eligible_count" == "0" ]]; then
    qualification_state="no_eligible_candidate"
    robustness_state="skipped_no_eligible_candidate"
    robustness_exit=0
  else
    qualification_state="eligible_candidate_available"
    # The current robustness implementation is intentionally candidate-specific.
    # Never silently apply the absorption_020 robustness suite to a different candidate.
    if [[ "$top_candidate" == "absorption_020" ]]; then
      /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_absorption_robustness_runtime || robustness_exit=$?
      if [[ $robustness_exit -eq 0 ]]; then
        robustness_state="evaluated_absorption_020"
      else
        robustness_state="failed_absorption_020"
      fi
    else
      echo "M5 robustness runner requires generalization for eligible candidate: $top_candidate" >&2
      robustness_state="blocked_candidate_runner_mismatch"
      robustness_exit=1
    fi
  fi
else
  robustness_exit=1
fi

# This is a one-shot Binance DEMO connectivity/execution proof, not strategy promotion.
# Its completed probe is now disabled; the runtime preserves terminal evidence and must not submit a new order while the probe config is disabled.
if [[ $robustness_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.binance_demo_execution_runtime || demo_exit=$?
else
  demo_exit=1
fi

if [[ $ablation_exit -ne 0 || $corpus_exit -ne 0 || $multiwindow_exit -ne 0 || $qualification_exit -ne 0 || $robustness_exit -ne 0 ]]; then
  echo "M5 research maintenance incomplete: ablation_exit=$ablation_exit corpus_exit=$corpus_exit multiwindow_exit=$multiwindow_exit qualification_exit=$qualification_exit qualification_state=$qualification_state robustness_exit=$robustness_exit robustness_state=$robustness_state demo_exit=$demo_exit" >&2
  exit 1
fi

if [[ $demo_exit -eq 0 ]]; then
  demo_state="terminal"
else
  demo_state="deferred"
fi

echo "M5 research maintenance complete: ablation=ok corpus=ok multiwindow=ok qualification=$qualification_state robustness=ok:$robustness_state demo=$demo_state"
