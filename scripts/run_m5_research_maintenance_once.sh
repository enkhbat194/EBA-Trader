#!/usr/bin/env bash
set -uo pipefail

cd /opt/Eba-Trader

ablation_exit=0
corpus_exit=0

/bin/bash /opt/Eba-Trader/scripts/run_m5_real_ablation_once.sh || ablation_exit=$?
/opt/Eba-Trader/.venv/bin/python -m eba_trader.m5_corpus_runtime || corpus_exit=$?

if [[ $ablation_exit -ne 0 || $corpus_exit -ne 0 ]]; then
  echo "M5 research maintenance incomplete: ablation_exit=$ablation_exit corpus_exit=$corpus_exit" >&2
  exit 1
fi

echo "M5 research maintenance complete: ablation=ok corpus=ok"
