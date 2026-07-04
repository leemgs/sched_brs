"""Adversarial robustness micro-benchmark (Sections IV-G and V-I).

Threat model. A CPU-bound task tries to inflate its interactivity score B_i by
alternating short sleeps with compute bursts, hoping to obtain an unfair CPU
share. Because the compute burst does *no* I/O, the adversary can only raise the
sleep-ratio component s_i of B_i and cannot fabricate the I/O-wait component w_i.

Experiment. On a saturated runqueue we run adversarial tasks against honest
CPU-bound co-runners (default 4 vs 12, mirroring the 16-core setup), sweep the
adversary's sleep duty cycle delta = T_sleep / (T_sleep + T_burst) over
{0.1, ..., 0.9}, and report, for the most advantageous duty cycle, the
adversary's CPU share and the worst-case co-runner slowdown -- compared against
CFS (alpha=beta=0) as a non-biased reference.

Expected result (paper): the bounded gain of Definition 1 caps the advantage at
the 1/(1 - alpha_max) ~= 1.54x factor of Lemma 1; the adversary's share stays a
few points above CFS rather than escalating into unbounded capture, and the
hybrid controller damps alpha as co-runner starvation rises.
"""

import os
from sched_brs_sim.scheduler import SchedulerSim, Task, ALPHA_MAX
from sched_brs_sim.metrics import deviation_bound
from sched_brs_sim.telemetry import write_csv


def build_workload(n_adv, n_honest, duty_cycle, period_ms=10.0):
    """Adversaries alternate sleep/burst at the given duty cycle; honest tasks
    are steady CPU-bound co-runners that never strategically sleep."""
    tasks = []
    for i in range(n_adv):
        # Fixed modest burst (comparable service to honest tasks): the adversary's
        # only lever is inflating s_i by sleeping at duty cycle `duty_cycle`. It
        # performs no I/O, so it cannot fabricate the w_i component of B_i.
        adv = Task(f"adv{i}", quantum=1.0, sleep_ratio=duty_cycle,
                   io_ratio=0.0, share=1.0 / (n_adv + n_honest))
        adv.is_adversary = True
        tasks.append(adv)
    for i in range(n_honest):
        h = Task(f"honest{i}", quantum=1.0, sleep_ratio=0.05, io_ratio=0.02,
                 share=1.0 / (n_adv + n_honest))
        h.is_adversary = False
        tasks.append(h)
    return tasks


def measure(policy_kwargs, n_adv, n_honest, duty_cycle, steps=15000):
    tasks = build_workload(n_adv, n_honest, duty_cycle)
    res = SchedulerSim(**policy_kwargs).run(tasks, steps=steps)
    shares = res["cpu_shares"]
    adv_share = sum(v for k, v in shares.items() if k.startswith("adv"))
    honest = {k: v for k, v in shares.items() if k.startswith("honest")}
    fair = 1.0 / (n_adv + n_honest)
    # Worst-case co-runner slowdown = fair_share / smallest_honest_share.
    min_honest = min(honest.values()) if honest else fair
    worst_slowdown = (fair / min_honest) if min_honest > 0 else float("inf")
    return adv_share, worst_slowdown, res["starvation_rate"]


def main(n_adv=4, n_honest=12):
    duties = [round(0.1 * i, 1) for i in range(1, 10)]
    rows = []
    best = None
    for d in duties:
        brs_share, brs_slow, brs_starv = measure(
            dict(alpha=0.20, beta=0.15, mode="hybrid", seed=23), n_adv, n_honest, d)
        cfs_share, cfs_slow, _ = measure(
            dict(alpha=0.0, beta=0.0, mode="static", seed=13), n_adv, n_honest, d)
        rows.append(dict(duty_cycle=d, brs_adv_share=round(brs_share, 4),
                         cfs_adv_share=round(cfs_share, 4),
                         brs_worst_slowdown=round(brs_slow, 3),
                         brs_starvation=round(brs_starv, 4)))
        if best is None or brs_share > best["brs_adv_share"]:
            best = rows[-1]

    os.makedirs("results", exist_ok=True)
    write_csv("results/adversarial.csv", rows,
              ["duty_cycle", "brs_adv_share", "cfs_adv_share",
               "brs_worst_slowdown", "brs_starvation"])
    bound = deviation_bound(ALPHA_MAX)
    print("Adversarial sweep (share of CPU captured by adversary):")
    for r in rows:
        print(f"  delta={r['duty_cycle']}: BRS {r['brs_adv_share']*100:5.1f}%  "
              f"CFS {r['cfs_adv_share']*100:5.1f}%  "
              f"worst co-runner slowdown {r['brs_worst_slowdown']:.2f}x")
    print(f"\nMost advantageous duty cycle for adversary: delta={best['duty_cycle']}"
          f"  BRS share={best['brs_adv_share']*100:.1f}%  "
          f"CFS share={best['cfs_adv_share']*100:.1f}%")
    print(f"Lemma 1 share-deviation bound 1/(1-alpha_max) = {bound:.2f}x "
          f"(worst observed slowdown {best['brs_worst_slowdown']:.2f}x should stay under it).")
    print("Wrote results/adversarial.csv")


if __name__ == "__main__":
    main()
