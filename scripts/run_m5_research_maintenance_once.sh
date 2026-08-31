#!/usr/bin/env bash
set -uo pipefail

cd /opt/Eba-Trader

ablation_exit=0
corpus_exit=0
sf1_exit=0
multiwindow_exit=0
activity_exit=0
qualification_exit=0
significance_exit=0
robustness_exit=0
sf2_exit=0
sf3_exit=0
demo_exit=0
sf1_state="deferred"
activity_state="deferred"
qualification_state="deferred"
significance_state="deferred"
robustness_state="deferred"
sf2_state="deferred"
sf3_state="deferred"

/bin/bash /opt/Eba-Trader/scripts/run_m5_real_ablation_once.sh || ablation_exit=$?
/opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_corpus_runtime || corpus_exit=$?

if [[ $corpus_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.sf1_runtime || sf1_exit=$?
  if [[ $sf1_exit -eq 0 ]]; then
    sf1_state="complete"
  else
    sf1_state="failed"
  fi
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_multiwindow_runtime || multiwindow_exit=$?
else
  sf1_exit=1
  sf1_state="blocked_corpus"
  multiwindow_exit=1
fi

if [[ $multiwindow_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_candidate_activity_runtime || activity_exit=$?
  if [[ $activity_exit -eq 0 ]]; then
    activity_state="complete"
  else
    activity_state="failed"
  fi
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_candidate_qualification_runtime || qualification_exit=$?
else
  activity_exit=1
  activity_state="blocked_multiwindow"
  qualification_exit=1
fi

if [[ $qualification_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_candidate_significance_runtime || significance_exit=$?
else
  significance_exit=1
fi

if [[ $significance_exit -eq 0 ]]; then
  significance_summary="$(/opt/Eba-Trader/.venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path('/var/lib/eba-trader/research/m5-candidate-significance-latest.json')
payload = json.loads(path.read_text(encoding='utf-8'))
if payload.get('phase') != 'COMPLETE' or payload.get('complete') is not True or payload.get('safe') is not True:
    raise SystemExit('significance status is not safely complete')
eligible = payload.get('eligibleCandidateCount')
significant = payload.get('significantCandidateCount')
top = payload.get('topSignificantCandidate')
state = payload.get('significanceState')
for name, value in (('eligibleCandidateCount', eligible), ('significantCandidateCount', significant)):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SystemExit(f'invalid {name}')
if significant > eligible:
    raise SystemExit('significant candidate count exceeds eligible count')
if significant == 0 and top is not None:
    raise SystemExit('zero significant candidates cannot have a top candidate')
if significant > 0 and (not isinstance(top, str) or not top):
    raise SystemExit('significant candidates require a top candidate')
print(f"{eligible}\t{significant}\t{top or '-'}\t{state or 'UNKNOWN'}")
PY
)" || significance_exit=$?
fi

if [[ $significance_exit -eq 0 ]]; then
  IFS=$'\t' read -r eligible_count significant_count top_candidate significance_result <<< "$significance_summary"
  if [[ "$eligible_count" == "0" ]]; then
    qualification_state="no_eligible_candidate"
    significance_state="no_eligible_candidate"
    robustness_state="skipped_no_eligible_candidate"
    robustness_exit=0
  elif [[ "$significant_count" == "0" ]]; then
    qualification_state="eligible_candidate_available"
    significance_state="no_significant_candidate"
    robustness_state="skipped_significance_gate"
    robustness_exit=0
  else
    qualification_state="eligible_candidate_available"
    significance_state="significant_candidate_available"
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
      echo "M5 robustness runner requires generalization for significant candidate: $top_candidate" >&2
      robustness_state="blocked_candidate_runner_mismatch"
      robustness_exit=1
    fi
  fi
else
  robustness_exit=1
fi

# SF2 is an independent fresh-development phase. It must not inherit authority from
# the legacy M5/SF1 candidate path and therefore runs regardless of that path's result.
# Its runtime can materialize only the preregistered development corpus and always
# publishes development-only evidence with Frozen OOS and live execution locked.
/opt/Eba-Trader/.venv/bin/python -m eba_trader.sf2_runtime || sf2_exit=$?
if [[ $sf2_exit -eq 0 ]]; then
  sf2_state="complete"
else
  sf2_state="failed"
fi

# SF3 is another independent fresh-development phase. It uses a distinct preregistered
# corpus and candidate set, cannot reuse SF1/SF2 evidence, and has no promotion authority.
# Its terminal evidence must keep Frozen OOS and live execution locked regardless of result.
/opt/Eba-Trader/.venv/bin/python -m eba_trader.sf3_runtime || sf3_exit=$?
if [[ $sf3_exit -eq 0 ]]; then
  sf3_state="complete"
else
  sf3_state="failed"
fi

# This is a one-shot Binance DEMO connectivity/execution proof, not strategy promotion.
# Its completed probe is now disabled; the runtime preserves terminal evidence and must not submit a new order while the probe config is disabled.
if [[ $robustness_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.binance_demo_execution_runtime || demo_exit=$?
else
  demo_exit=1
fi

if [[ $ablation_exit -ne 0 || $corpus_exit -ne 0 || $sf1_exit -ne 0 || $multiwindow_exit -ne 0 || $activity_exit -ne 0 || $qualification_exit -ne 0 || $significance_exit -ne 0 || $robustness_exit -ne 0 || $sf2_exit -ne 0 || $sf3_exit -ne 0 ]]; then
  echo "M5/SF1/SF2/SF3 research maintenance incomplete: ablation_exit=$ablation_exit corpus_exit=$corpus_exit sf1_exit=$sf1_exit sf1_state=$sf1_state multiwindow_exit=$multiwindow_exit activity_exit=$activity_exit activity_state=$activity_state qualification_exit=$qualification_exit qualification_state=$qualification_state significance_exit=$significance_exit significance_state=$significance_state robustness_exit=$robustness_exit robustness_state=$robustness_state sf2_exit=$sf2_exit sf2_state=$sf2_state sf3_exit=$sf3_exit sf3_state=$sf3_state demo_exit=$demo_exit" >&2
  exit 1
fi

if [[ $demo_exit -eq 0 ]]; then
  demo_state="terminal"
else
  demo_state="deferred"
fi

echo "M5/SF1/SF2/SF3 research maintenance complete: ablation=ok corpus=ok sf1=$sf1_state multiwindow=ok activity=$activity_state qualification=$qualification_state significance=$significance_state robustness=ok:$robustness_state sf2=$sf2_state sf3=$sf3_state demo=$demo_state"
