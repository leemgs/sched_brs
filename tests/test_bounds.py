"""Regression tests for the BRS reference simulator's formal guarantees.

These check the properties the paper actually proves, so a future edit that
silently breaks the mechanism (e.g. flipping the sign of Eq. 2 back to
1 + alpha*B) fails loudly:

  * Definition 1  bounded bias:   (1 - alpha_max) dt <= dvruntime <= dt
  * Lemma 1       share deviation within 1/(1 - alpha_max)
  * Section IV-C  interactivity score B_i in [0, 1], convex weights sum to 1
  * Eq. (2) sign  interactive (high-B) tasks accrue vruntime *more slowly*
  * CFS reduction alpha = beta = 0 reproduces unbiased vruntime
  * Fairness floor J >= 0.96 and bounded starvation on a saturated runqueue

Pure stdlib unittest, no third-party dependencies.
"""

import random
import unittest

from sched_brs_sim.scheduler import (SchedulerSim, Task,
                                      ALPHA_MIN, ALPHA_MAX, BETA_MIN, BETA_MAX)
from sched_brs_sim.interactivity import (InteractivityEstimator,
                                         LAMBDA1_SLEEP, LAMBDA2_IOWAIT, LAMBDA3_HISTORY)
from sched_brs_sim.metrics import deviation_bound, jains_index
from sched_brs_sim.workloads import interactive_workload, gaming_workload


class TestInteractivityScore(unittest.TestCase):
    def test_convex_weights_sum_to_one(self):
        self.assertAlmostEqual(LAMBDA1_SLEEP + LAMBDA2_IOWAIT + LAMBDA3_HISTORY, 1.0)

    def test_score_bounded_under_random_events(self):
        rng = random.Random(0)
        est = InteractivityEstimator()
        for _ in range(2000):
            t_sleep = rng.uniform(0, 5)
            t_run = rng.uniform(0, 5)
            t_iowait = rng.uniform(0, t_sleep)
            B = est.observe(t_sleep=t_sleep, t_run=t_run, t_iowait=t_iowait,
                            woke=rng.random() < 0.3)
            self.assertGreaterEqual(B, 0.0)
            self.assertLessEqual(B, 1.0)

    def test_sleepy_task_scores_higher_than_cpu_bound(self):
        sleepy = InteractivityEstimator()
        hog = InteractivityEstimator()
        for _ in range(200):
            sleepy.observe(t_sleep=4.0, t_run=0.5, t_iowait=2.0, woke=True)
            hog.observe(t_sleep=0.0, t_run=4.0, t_iowait=0.0, woke=False)
        self.assertGreater(sleepy.score, hog.score)
        self.assertLess(hog.score, 0.2)


class TestDefinition1Bound(unittest.TestCase):
    """dvruntime = dt * (1 - alpha*B) must lie in [(1-alpha_max)dt, dt]."""

    def test_delta_within_bound_over_grid(self):
        dt = 1.0
        for a in (ALPHA_MIN, 0.2, ALPHA_MAX):
            sim = SchedulerSim(alpha=a, beta=0.15, mode="static")
            for B in (0.0, 0.25, 0.5, 0.75, 1.0):
                dv = sim._bounded_vruntime_delta(dt, B)
                self.assertLessEqual(dv, dt + 1e-12)
                self.assertGreaterEqual(dv, (1.0 - ALPHA_MAX) * dt - 1e-12)
                self.assertGreater(dv, 0.0)  # strictly positive (Lemma 1)

    def test_sign_is_correct_high_B_slows_vruntime(self):
        # The whole mechanism: a more-interactive task must accrue vruntime
        # *more slowly*, so its delta is smaller. Guards against the 1+aB bug.
        sim = SchedulerSim(alpha=0.3, beta=0.15, mode="static")
        dv_low = sim._bounded_vruntime_delta(1.0, 0.1)
        dv_high = sim._bounded_vruntime_delta(1.0, 0.9)
        self.assertLess(dv_high, dv_low)

    def test_cfs_reduction(self):
        # alpha = 0 must reproduce plain vruntime (delta == dt) for any B.
        sim = SchedulerSim(alpha=0.0, beta=0.0, mode="static")
        for B in (0.0, 0.5, 1.0):
            self.assertAlmostEqual(sim._bounded_vruntime_delta(1.0, B), 1.0)


class TestLemma1ShareBound(unittest.TestCase):
    def test_deviation_bound_formula(self):
        self.assertAlmostEqual(deviation_bound(0.35), 1.0 / (1.0 - 0.35))
        # ~1.54x figure quoted in the paper.
        self.assertAlmostEqual(deviation_bound(ALPHA_MAX), 1.538, places=3)

    def test_deviation_bound_monotone_in_alpha(self):
        self.assertLess(deviation_bound(0.10), deviation_bound(0.35))


class TestJainsIndex(unittest.TestCase):
    def test_perfectly_equal_is_one(self):
        self.assertAlmostEqual(jains_index([1.0, 1.0, 1.0, 1.0]), 1.0)

    def test_single_hog_is_low(self):
        self.assertLess(jains_index([10.0, 0.0, 0.0, 0.0, 0.0]), 0.3)


class TestSchedulerIntegration(unittest.TestCase):
    """Smoke tests: on a saturated runqueue BRS keeps fairness above the floor,
    bounds starvation, and does not make the interactive tail *worse* than CFS."""

    def _run(self, workload_fn, **kw):
        return SchedulerSim(**kw).run(workload_fn(), steps=8000)

    def test_fairness_floor_and_starvation(self):
        for wf in (interactive_workload, gaming_workload):
            res = self._run(wf, alpha=0.2, beta=0.15, mode="hybrid", seed=1)
            self.assertGreaterEqual(res["fairness_jain"], 0.96)
            self.assertLessEqual(res["starvation_rate"], 0.05)

    def test_brs_improves_interactive_tail_vs_cfs(self):
        cfs = self._run(interactive_workload, alpha=0.0, beta=0.0,
                        mode="static", seed=1)
        brs = self._run(interactive_workload, alpha=0.2, beta=0.15,
                        mode="hybrid", seed=1)
        # Interactive-class P95 should not regress under BRS.
        self.assertLessEqual(brs["p95_latency"], cfs["p95_latency"] + 1e-9)

    def test_safe_box_projection(self):
        # After a hybrid run the controller's iterates stay in the Table I box.
        res = self._run(gaming_workload, alpha=0.2, beta=0.15,
                        mode="hybrid", seed=7)
        self.assertGreaterEqual(res["alpha"], ALPHA_MIN - 1e-9)
        self.assertLessEqual(res["alpha"], ALPHA_MAX + 1e-9)
        self.assertGreaterEqual(res["beta"], BETA_MIN - 1e-9)
        self.assertLessEqual(res["beta"], BETA_MAX + 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
