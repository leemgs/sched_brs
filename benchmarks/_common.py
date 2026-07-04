"""Shared benchmark runner.

Runs three policies over a workload and writes a scalar CSV plus a JSON with
full per-task detail. Policies:
  * cfs  -- alpha=beta=0, static (proportional-fair baseline)
  * bfs  -- a low-latency, less-fair static bias (BFS/MuQSS-like reference)
  * brs  -- alpha=0.20, beta=0.15, hybrid (paper defaults, Table I)
"""

import os
from sched_brs_sim.scheduler import SchedulerSim
from sched_brs_sim.telemetry import write_csv, write_json

SCALAR_FIELDS = [
    "policy", "p95_latency", "p95_latency_all", "p95_latency_interactive",
    "p95_latency_background", "p99_latency", "fairness_jain",
    "starvation_rate", "alpha", "beta",
]


def _scalars(policy, res):
    row = {"policy": policy}
    for k in SCALAR_FIELDS:
        if k != "policy":
            row[k] = res.get(k, "")
    return row


def run_workload(name, workload_fn, steps=12000):
    make = workload_fn
    cfs = SchedulerSim(alpha=0.0,  beta=0.0,  mode="static", seed=13).run(make(), steps=steps)
    bfs = SchedulerSim(alpha=0.30, beta=0.25, mode="static", seed=17).run(make(), steps=steps)
    brs = SchedulerSim(alpha=0.20, beta=0.15, mode="hybrid", seed=23).run(make(), steps=steps)

    rows = [_scalars("cfs", cfs), _scalars("bfs", bfs), _scalars("brs", brs)]
    out_csv = f"results/{name}.csv"
    write_csv(out_csv, rows, SCALAR_FIELDS)
    write_json(f"results/{name}_detail.json", {
        "cfs": {k: cfs[k] for k in ("cpu_shares", "sched_counts")},
        "brs": {k: brs[k] for k in ("cpu_shares", "sched_counts")},
    })
    print(f"Wrote {out_csv}")
    return rows
