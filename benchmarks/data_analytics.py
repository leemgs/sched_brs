import os, json
from sched_brs_sim.scheduler import SchedulerSim
from sched_brs_sim.workloads import data_analytics_workload
from sched_brs_sim.telemetry import write_csv

def run_one(policy, **kwargs):
    sim = SchedulerSim(**kwargs)
    tasks = data_analytics_workload()
    return sim.run(tasks, steps=8000)

def main():
    rows = []
    # Baselines: CFS-like (no bias), BFS-like (interactive favoritism), and SCHED_BRS (hybrid)
    res_cfs = run_one("cfs", alpha=0.0, beta=0.0, mode="static", seed=13)
    res_bfs = run_one("bfs", alpha=0.10, beta=0.10, mode="static", seed=17)
    res_tek = run_one("sched_brs_hybrid", alpha=0.20, beta=0.15, mode="hybrid", seed=23)
    rows.append(dict(policy="cfs", **res_cfs))
    rows.append(dict(policy="bfs", **res_bfs))
    rows.append(dict(policy="sched_brs_hybrid", **res_tek))

    out = f"results/data_analytics.csv"
    header = sorted({k for k in rows[0].keys()} | {"policy"})
    write_csv(out, rows, header)
    print(f"Wrote {out}")

if __name__ == "__main__":
    name = "data_analytics"
    main()
