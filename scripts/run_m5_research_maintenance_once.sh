#!/usr/bin/env bash
set -uo pipefail

cd /opt/Eba-Trader

ablation_exit=0
corpus_exit=0
multiwindow_exit=0
robustness_exit=0

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

if [[ $ablation_exit -ne 0 || $corpus_exit -ne 0 || $multiwindow_exit -ne 0 || $robustness_exit -ne 0 ]]; then
  echo "M5 research maintenance incomplete: ablation_exit=$ablation_exit corpus_exit=$corpus_exit multiwindow_exit=$multiwindow_exit robustness_exit=$robustness_exit" >&2
  exit 1
fi

echo "M5 research maintenance complete: ablation=ok corpus=ok multiwindow=ok robustness=ok"
