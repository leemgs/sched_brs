# SCHED_BRS Artifact (Reproduction Package)

This repository contains a faithful, **runnable simulator**, benchmark harness, and analysis scripts that reproduce the core findings and figures logic from the SCHED_TEK paper. It also ships a placeholder kernel patch showing how the bias hooks are integrated; you can replace it with your production patch when ready.

> Paper reference: “Responsiveness Is Not a Trade-Off: Revisiting Kernel Scheduling with Controlled Bias.” fileciteturn0file0

## What’s inside
- `sched_brs_sim/` — Python simulator of the bounded-bias scheduler (vruntime bias, tie-breaker, hybrid controller with fairness floor & starvation cap).
- `benchmarks/` — Synthetic yet representative workloads (interactive, gaming/graphics, AI inference, streaming, analytics) and a `run_all.sh` that emits CSVs to `results/`.
- `scripts/` — `analyze_results.py` to compute P95 latency, Jain’s index, starvation rate, and Perf/W proxies from CSVs.
- `kernel_patches/` — A minimal patch sketch (`sched_brs.patch`) with the expected CFS touch points, guards, and `/proc/sys/kernel/sched_brs` knobs.
- `ci/` — A lightweight CI script that runs the simulator and basic regression checks.
- `results/` — Output directory for generated CSVs and summaries.
- `LICENSE.md` — Apache-2.0.

## Quick start
```bash
# 1) Create a venv (optional but recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip

# 2) Run all benchmarks (simulator-based) — generates CSVs in results/
bash benchmarks/run_all.sh

# 3) Analyze outputs and print a summary to console (also writes JSON report)
python scripts/analyze_results.py --input results --out results/summary.json
```

You should see per-workload improvements (P95 ↓, starvation kept low, fairness ≥ 0.96 in hybrid mode), consistent with the paper’s narrative. Exact numbers will differ from kernel measurements but follow the same trends. fileciteturn0file0

## Using the kernel patch sketch
- `kernel_patches/sched_tek.patch` shows where vruntime scaling and a tie‑breaker can be added inside `kernel/sched/fair.c` (illustrative diff).
- It also sketches a `/proc/sys/sched_tek/*` interface (`bias_alpha`, `bias_beta`, `bias_mode`, TTL/boost knobs).
- Replace the sketch with your real patch when ready; the repo structure matches the paper’s artifact layout for easy swap‑in. fileciteturn0file0

## Reproducing figures/tables logic
Run:
```bash
bash benchmarks/run_all.sh
python scripts/analyze_results.py --input results --out results/summary.json
```
This regenerates:
- P95 latency deltas vs. a “CFS-like” policy (sim baseline) and a BFS‑like policy (less fairness). 
- Jain’s index, starvation %, and perf/watt proxies (work-normalized throughput per joule unit).

The simulator encodes SCHED_TEK’s hybrid controller and bounded bias consistent with the paper’s pseudocode and playbook defaults (α=0.20, β=0.15; J_min=0.96; starvation cap 2%). fileciteturn0file0

## Folder structure
```
sched_tek_artifact/
├─ README.md
├─ LICENSE.md
├─ kernel_patches/
│  └─ sched_tek.patch
├─ sched_tek_sim/
│  ├─ __init__.py
│  ├─ scheduler.py
│  ├─ workloads.py
│  ├─ metrics.py
│  └─ telemetry.py
├─ benchmarks/
│  ├─ run_all.sh
│  ├─ interactive.py
│  ├─ gaming.py
│  ├─ ai_inference.py
│  ├─ data_analytics.py
│  └─ streaming.py
├─ scripts/
│  ├─ analyze_results.py
│  └─ run_gui_redraw.sh
├─ ci/
│  └─ run_tests.sh
└─ results/
   └─ .gitkeep
```

## License
Apache-2.0. See `LICENSE.md`.
