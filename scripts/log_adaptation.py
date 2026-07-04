"""Controller adaptation trajectory logger (Section V-H).

Theorem 1 predicts the hybrid controller converges in mean square to a
neighbourhood of the optimum. Section V-H validates this empirically by logging
the (alpha_t, beta_t) trajectories together with J_t and the starvation rate
S_t across abrupt workload transitions (idle -> gaming -> mixed contention),
observing that the controller settles within 3-5 control periods and that the
fairness/starvation signals never cross their guardrails during adaptation.

This script reproduces that experiment with the reference simulator. A single
SchedulerSim instance is carried across the phases so the controller state
(alpha, beta) persists through each transition -- the controller must re-settle
from wherever the previous phase left it, which is the point of the experiment.

The controller runs on a *noisy* fairness estimate (Eq. 3: J_hat = J + xi),
enabled here via meas_noise, so the logged trajectory exhibits the bounded
bang-bang jitter around the operating point that Theorem 1 characterises,
rather than a noise-free ramp. The raw (t, alpha, beta, J, S) traces are written
to results/adaptation/ so the curves can be reproduced.
"""

import os

from sched_brs_sim.scheduler import SchedulerSim
from sched_brs_sim.workloads import gaming_workload
from sched_brs_sim.telemetry import write_csv, write_json


def _idle_workload():
    """Lightly loaded, *balanced* runqueue: a handful of homogeneous interactive
    tasks that mostly sleep. Shares stay even (high J) and latency pressure is
    low, so the controller faces no guardrail stress -- the baseline state the
    idle->gaming transition departs from."""
    from sched_brs_sim.scheduler import Task
    return [Task(f"idle{i}", quantum=0.6, sleep_ratio=0.85, io_ratio=0.30,
                 share=1.0 / 6) for i in range(6)]


def _mixed_contention_workload():
    """Heavy mixed contention: interactive foreground contends with a large
    CPU-bound background plus strategically-sleeping tasks, saturating the
    runqueue so the controller must arbitrate under pressure."""
    from sched_brs_sim.scheduler import Task
    tasks = [
        Task("ui",      quantum=0.5, sleep_ratio=0.88, io_ratio=0.30, share=0.05),
        Task("render",  quantum=0.7, sleep_ratio=0.75, io_ratio=0.20, share=0.05),
        Task("frame",   quantum=0.6, sleep_ratio=0.70, io_ratio=0.15, share=0.05),
    ]
    for i in range(9):
        tasks.append(Task(f"cpu{i}", quantum=1.3 + 0.1 * i, sleep_ratio=0.08,
                          io_ratio=0.03, share=0.05))
    for i in range(4):
        tasks.append(Task(f"burst{i}", quantum=1.0, sleep_ratio=0.55,
                          io_ratio=0.0, share=0.05))
    return tasks


def run_phase(sim, name, workload_fn, periods, t_offset, steps_per_period=1200):
    """Run one workload phase, returning its (offset) trajectory rows."""
    res = sim.run(workload_fn(), steps=periods * steps_per_period, log_trajectory=True)
    rows = []
    for (t, a, b, J, S) in res["trajectory"]:
        rows.append(dict(phase=name, t_ms=round(t_offset + t, 1),
                         alpha=round(a, 4), beta=round(b, 4),
                         jain=round(J, 4), starvation=round(S, 4)))
    return rows, res


def _settle_period(rows, tol=1e-9):
    """Index (1-based, within phase) of the first control period after which
    alpha and beta stop changing -- an empirical 'settling time'."""
    if not rows:
        return None
    last_a, last_b = rows[-1]["alpha"], rows[-1]["beta"]
    settle = len(rows)
    for i in range(len(rows) - 1, -1, -1):
        if abs(rows[i]["alpha"] - last_a) < tol and abs(rows[i]["beta"] - last_b) < tol:
            settle = i + 1
        else:
            break
    return settle


def main():
    # One controller instance persists across all transitions. A small
    # measurement noise reproduces the realistic jittering trajectory of
    # Theorem 1; the seed makes it reproducible.
    sim = SchedulerSim(alpha=0.20, beta=0.15, mode="hybrid",
                       latency_target_ms=12.4, delta_a=0.04, delta_b=0.04,
                       meas_noise=0.02, seed=2026)

    phases = [
        ("idle", _idle_workload, 8),
        ("gaming", gaming_workload, 12),
        ("mixed_contention", _mixed_contention_workload, 12),
    ]

    all_rows = []
    t_offset = 0.0
    summary = []
    for name, fn, periods in phases:
        rows, res = run_phase(sim, name, fn, periods, t_offset)
        all_rows.extend(rows)
        if rows:
            t_offset = rows[-1]["t_ms"]
        settle = _settle_period(rows)
        summary.append(dict(
            phase=name,
            periods=len(rows),
            final_alpha=rows[-1]["alpha"] if rows else None,
            final_beta=rows[-1]["beta"] if rows else None,
            min_jain=min((r["jain"] for r in rows), default=None),
            max_starvation=max((r["starvation"] for r in rows), default=None),
            settle_period=settle,
        ))

    os.makedirs("results/adaptation", exist_ok=True)
    write_csv("results/adaptation/trajectory.csv", all_rows,
              ["phase", "t_ms", "alpha", "beta", "jain", "starvation"])
    write_json("results/adaptation/summary.json", {"phases": summary})

    print("Controller adaptation across workload transitions (Sec V-H):")
    print(f"{'phase':<18}{'periods':>8}{'alpha*':>9}{'beta*':>8}"
          f"{'min J':>9}{'max S':>9}{'settle':>8}")
    for s in summary:
        print(f"{s['phase']:<18}{s['periods']:>8}{s['final_alpha']:>9.3f}"
              f"{s['final_beta']:>8.3f}{s['min_jain']:>9.4f}"
              f"{s['max_starvation']:>9.4f}{str(s['settle_period']):>8}")
    floor_ok = all(s["min_jain"] >= 0.96 for s in summary)
    starv_ok = all(s["max_starvation"] <= 0.012 for s in summary)
    print(f"\nFairness floor (J >= 0.96) held throughout: {floor_ok}")
    print(f"Starvation stayed below 1.2%: {starv_ok}")
    print("Wrote results/adaptation/trajectory.csv and summary.json")


if __name__ == "__main__":
    main()
