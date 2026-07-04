#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT:${PYTHONPATH-}"
cd "$ROOT"
PY=python

echo "[CI] byte-compiling sources"
$PY -m py_compile sched_brs_sim/*.py scripts/*.py benchmarks/*.py

echo "[CI] unit + regression tests (Def.1 bound, Lemma 1, B_i in [0,1], Eq.2 sign)"
$PY -m unittest discover -s tests -v

echo "[CI] benchmark suite (incl. adversarial)"
bash benchmarks/run_all.sh

echo "[CI] result analysis"
$PY scripts/analyze_results.py --input results --out results/summary.json

echo "[CI] DOE surrogate fit + closed-form tuning (Sec IV-I)"
$PY scripts/doe_sweep.py

echo "[CI] controller adaptation traces (Sec V-H)"
$PY scripts/log_adaptation.py

echo "[CI] synthetic AI dataset (Sec V-C)"
$PY scripts/gen_synth.py

echo "[CI] all checks passed."
