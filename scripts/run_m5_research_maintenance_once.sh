#!/usr/bin/env bash
set -uo pipefail

cd /opt/Eba-Trader

ablation_exit=0
corpus_exit=0
multiwindow_exit=0
robustness_exit=0
demo_exit=0

/bin/bash /opt/Eba-Trader/scripts/run_m5_real_ablation_once.sh || ablation_exit=$?
/opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_corpus_runtime || corpus_exit=$?

if [[ $corpus_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_multiwindow_runtime || multiwindow_exit=$?
else
  multiwindow_exit=1
fi

if [[ $multiwindow_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_absorption_robustness_runtime || robustness_exit=$?
else
  robustness_exit=1
fi

# This is a one-shot Binance DEMO connectivity/execution proof, not strategy promotion.
# Its terminal failure is evidence to inspect; it must not trigger service retries that
# could submit another exchange order. The runtime itself is idempotent by probe_id.
if [[ $robustness_exit -eq 0 ]]; then
  /opt/Eba-Trader/.venv/bin/python -m eba_trader.binance_demo_execution_runtime || demo_exit=$?
else
  demo_exit=1
fi

if [[ $ablation_exit -ne 0 || $corpus_exit -ne 0 || $multiwindow_exit -ne 0 || $robustness_exit -ne 0 ]]; then
  echo "M5 research maintenance incomplete: ablation_exit=$ablation_exit corpus_exit=$corpus_exit multiwindow_exit=$multiwindow_exit robustness_exit=$robustness_exit demo_exit=$demo_exit" >&2
  exit 1
fi

if [[ $demo_exit -eq 0 ]]; then
  demo_state="terminal"
else
  demo_state="deferred"
fi

echo "M5 research maintenance complete: ablation=ok corpus=ok multiwindow=ok robustness=ok demo=$demo_state"
