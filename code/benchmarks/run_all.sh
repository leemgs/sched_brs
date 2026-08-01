#!/usr/bin/env bash
set -euo pipefail
PY=python
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT:${PYTHONPATH-}"
cd "$ROOT"

$PY benchmarks/interactive.py
$PY benchmarks/gaming.py
$PY benchmarks/ai_inference.py
$PY benchmarks/data_analytics.py
$PY benchmarks/streaming.py
$PY benchmarks/adversarial.py

echo "[OK] All benchmarks finished. See results/ for CSVs."
