"""Metric helpers used across the BRS simulator and analysis scripts.

Definitions follow Section V-A of the paper:
  * P95 / P99 scheduling latency  = percentile of per-task wake-up-to-run delay.
  * Jain's fairness index J       = (sum x_i)^2 / (n * sum x_i^2)  over CPU shares.
  * Starvation                    = a runnable task undispatched for > 100 ms.
"""

import math


def percentile(xs, q):
    """Linear-interpolation percentile, q in [0, 100]."""
    if not xs:
        return 0.0
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    rank = (q / 100.0) * (len(xs) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return xs[lo]
    frac = rank - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def p95(xs):
    return percentile(xs, 95.0)


def p99(xs):
    return percentile(xs, 99.0)


def jains_index(shares):
    """Jain's fairness index over per-task CPU shares (Eq. in Notation para)."""
    shares = [s for s in shares]
    s1 = sum(shares)
    s2 = sum(x * x for x in shares)
    if s2 == 0:
        return 1.0
    n = len(shares) if shares else 1
    return (s1 * s1) / (n * s2)


def perf_per_watt(throughput, watts):
    if watts <= 0:
        return 0.0
    return throughput / watts


def worst_case_slowdown(shares_brs, shares_cfs):
    """Worst-case single-task completion-time slowdown normalised to CFS.

    A task that receives a smaller CPU share finishes proportionally later, so
    slowdown_i = share_cfs_i / share_brs_i.  Returns the maximum over tasks
    (the deliberate worst case reported in Section V-D).
    """
    worst = 1.0
    for name in shares_cfs:
        b = shares_brs.get(name, 0.0)
        c = shares_cfs.get(name, 0.0)
        if b > 0 and c > 0:
            worst = max(worst, c / b)
    return worst


def deviation_bound(alpha_max):
    """Definition 1 / Lemma 1 multiplicative share-deviation bound 1/(1-a_max)."""
    return 1.0 / (1.0 - alpha_max)
