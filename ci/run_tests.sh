#!/usr/bin/env bash
set -euo pipefail
python -m py_compile sched_brs_sim/*.py
bash benchmarks/run_all.sh
python scripts/analyze_results.py --input results --out results/summary.json
echo "[CI] basic simulation + analysis succeeded."
