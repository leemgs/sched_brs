"""Bounded Responsiveness Scheduler (BRS) reference simulator.

This is a lightweight single-CPU weighted-fair-queuing simulator that faithfully
implements the mechanisms described in the paper:

  * Eq. (2)  bounded vruntime update:  v_i <- v_i + dt * (1 - alpha * B_i)
  * Sec IV-C interactivity score B_i   (see interactivity.InteractivityEstimator)
  * Sec IV-D interactivity-aware tie-breaker: pick argmin_i (v_i - beta * B_i)
  * Sec IV-F hybrid controller + aging guardrail (starvation shield)
  * Def. 1   bounded bias:  (1 - alpha_max) dt <= dvruntime <= dt
  * Lemma 1  order & share preservation (1 - alpha*B_i > 0)
  * Alg. 1   Phase 1 (vruntime) / Phase 2 (selection) / Phase 3 (safety rails)

Exact numbers differ from real kernel measurements, but the *trends* and the
*mechanism* match the paper: interactive (high-B_i) tasks see lower wake-to-run
tail latency, while fairness stays above the floor and starvation stays bounded.
"""

import random

from .metrics import p95, p99, jains_index
from .interactivity import InteractivityEstimator

# Table I: sensible defaults and safe parameter ranges.
ALPHA_DEFAULT, ALPHA_MIN, ALPHA_MAX = 0.20, 0.10, 0.35
BETA_DEFAULT, BETA_MIN, BETA_MAX = 0.15, 0.05, 0.30

# Section V-A operational definitions.
STARVATION_LATENCY_MS = 100.0   # runnable but undispatched for > 100 ms
CONTROL_PERIOD_MS = 1000.0      # T_c, default 1 s

# CFS-style sleeper credit (mirrors place_entity()): a waking task is re-placed
# near the runqueue's min_vruntime with a bounded bonus, so a task cannot bank
# unlimited priority just by sleeping (this is the baseline both CFS and BRS
# share; BRS's advantage then comes only from the bounded bias, per the paper).
SLEEPER_CREDIT_MS = 0.5         # bounded sleeper bonus (< min_granularity)


class Task:
    """A schedulable entity with a configurable sleep/I-O propensity.

    The propensities drive the sleep behaviour of the discrete-event model; the
    interactivity score B_i is then *measured* from the resulting behaviour by
    an InteractivityEstimator, exactly as the kernel would derive it from
    se.statistics rather than from a static label.
    """

    def __init__(self, name, quantum=1.0, sleep_ratio=0.0, io_ratio=0.0,
                 share=0.1, window=64, rho=0.25):
        self.name = name
        self.quantum = float(quantum)          # run burst length (ms)
        self.sleep_ratio = float(sleep_ratio)  # propensity to sleep after a burst
        self.io_ratio = float(io_ratio)        # fraction of sleep that is I/O wait
        self.share = float(share)              # nominal weight (reference only)
        # Live scheduler state.
        self.v = 0.0                # virtual runtime
        self.runnable = True
        self.wake_time = 0.0        # last wake timestamp (for wake-to-run latency)
        self.wait_start = 0.0       # when it last became runnable & undispatched
        self.sleep_until = 0.0
        self.cpu_time = 0.0         # accumulated real CPU time (for shares)
        self.est = InteractivityEstimator(window=window, rho=rho)
        self.B = 0.0

    @property
    def recent_wakeup(self):  # kept for backward-compat with older callers
        return self.est.score > 0.5


class SchedulerSim:
    """Discrete-event BRS simulator.

    mode:
      * 'static'   fixed (alpha, beta), no feedback  (alpha=beta=0 emulates CFS)
      * 'adaptive' Sec IV-F proportional law only
      * 'hybrid'   Alg. 1 Phase 3 damp/promote + aging guardrail (recommended)
    """

    def __init__(self, alpha=ALPHA_DEFAULT, beta=BETA_DEFAULT, mode='hybrid',
                 j_min=0.96, j_max=0.97, starvation_cap=0.02,
                 latency_target_ms=8.0, delta_a=0.02, delta_b=0.02,
                 control_period_ms=CONTROL_PERIOD_MS, meas_noise=0.0, seed=42):
        self.alpha0, self.beta0 = alpha, beta
        self.alpha, self.beta = alpha, beta
        self.mode = mode
        self.j_min, self.j_max = j_min, j_max
        self.starvation_cap = starvation_cap
        self.latency_target_ms = latency_target_ms
        self.delta_a, self.delta_b = delta_a, delta_b
        self.control_period_ms = control_period_ms
        # Zero-mean measurement noise on the controller's *observed* fairness
        # signal, modelling J_hat_t = J(theta_t) + xi_t of Eq. (3) / Theorem 1.
        # Default 0.0 keeps benchmarks and the DOE sweep deterministic; the
        # adaptation logger (Sec V-H) turns it on to reproduce the realistic
        # jittering trajectory the mean-square-stability result describes.
        self.meas_noise = meas_noise
        self.rng = random.Random(seed)

    # ----- Phase 1 helper: bounded vruntime update (Eq. 2) -----
    def _bounded_vruntime_delta(self, dt, B):
        # 1 - alpha*B_i is strictly positive & bounded in [1-alpha_max, 1]
        # (Lemma 1), so vruntime is strictly increasing in dt.
        return dt * (1.0 - self.alpha * B)

    def run(self, tasks, steps=10000, log_trajectory=False):
        now = 0.0
        min_vruntime = 0.0
        lat_samples = []
        lat_interactive = []   # tail for latency-sensitive tasks (paper headline)
        lat_background = []
        starvation_events = 0
        starving_tasks = set()
        # Rolling fairness/latency window for the controller.
        recent_lat = []
        window_cpu = {t.name: 0.0 for t in tasks}
        next_control = self.control_period_ms
        trajectory = []  # (t, alpha, beta, J, S) per control period

        for t in tasks:
            t.v = 0.0
            t.runnable = True
            t.wake_time = 0.0
            t.wait_start = 0.0
            t.sleep_until = 0.0
            t.cpu_time = 0.0

        for step in range(steps):
            # Wake any tasks whose sleep timer just expired. On wake, re-place
            # the task near min_vruntime with a bounded sleeper credit (CFS
            # place_entity semantics) so sleeping cannot bank unlimited credit.
            for t in tasks:
                if not t.runnable and t.sleep_until <= now:
                    t.runnable = True
                    t.wake_time = now
                    t.wait_start = now
                    t.v = max(t.v, min_vruntime - SLEEPER_CREDIT_MS)
                    t.est.observe(t_sleep=0.0, t_run=0.0, woke=True)
            runnable = [t for t in tasks if t.runnable]
            if not runnable:
                # Idle: advance to the earliest wake-up (never busy-idle a CPU).
                nxt = min(t.sleep_until for t in tasks if not t.runnable)
                now = max(now + 1.0, nxt)
                continue
            min_vruntime = min(t.v for t in runnable)

            # ----- Phase 3 (aging guardrail): force-promote a starved task -----
            aged = [t for t in runnable if (now - t.wait_start) > STARVATION_LATENCY_MS]
            if aged:
                chosen = max(aged, key=lambda t: now - t.wait_start)
                # Starvation shield: pull vruntime to the runqueue minimum.
                chosen.v = min(t.v for t in runnable)
            else:
                # ----- Phase 2: interactivity-aware selection -----
                chosen = min(runnable, key=lambda t: t.v - self.beta * t.B)

            # Scheduling latency = requeue-to-run delay (Section V-A), i.e. how
            # long the dispatched task waited since it last became runnable.
            latency = now - chosen.wait_start
            # Small measurement jitter, seed-deterministic.
            latency += max(0.0, self.rng.lognormvariate(0.0, 0.25) - 0.9)
            lat_samples.append(latency)
            if chosen.sleep_ratio >= 0.5:      # latency-sensitive / interactive
                lat_interactive.append(latency)
            else:
                lat_background.append(latency)
            recent_lat.append(latency)
            if len(recent_lat) > 500:
                recent_lat.pop(0)

            # Run the chosen task for one burst.
            dt = chosen.quantum
            chosen.B = chosen.est.observe(t_sleep=0.0, t_run=dt, woke=False)
            # ----- Phase 1: bounded vruntime update (Eq. 2) -----
            chosen.v += self._bounded_vruntime_delta(dt, chosen.B)
            chosen.cpu_time += dt
            window_cpu[chosen.name] += dt
            now += dt

            # Decide whether the task sleeps (interactive) or stays runnable.
            if self.rng.random() < chosen.sleep_ratio:
                # Sleep duration scaled so high sleep_ratio => longer, frequent sleeps.
                sleep_len = chosen.quantum * (1.0 + 3.0 * chosen.sleep_ratio)
                io = sleep_len * chosen.io_ratio
                chosen.est.observe(t_sleep=sleep_len, t_run=0.0, t_iowait=io, woke=False)
                chosen.runnable = False
                chosen.sleep_until = now + sleep_len
            else:
                chosen.wait_start = now  # re-queued immediately, resets its wait

            # Starvation accounting for the tasks left waiting.
            for t in runnable:
                if t is chosen:
                    continue
                if (now - t.wait_start) > STARVATION_LATENCY_MS and t.name not in starving_tasks:
                    starvation_events += 1
                    starving_tasks.add(t.name)
                elif (now - t.wait_start) <= STARVATION_LATENCY_MS:
                    starving_tasks.discard(t.name)

            # ----- Phase 3: hybrid control, once per control period T_c -----
            if now >= next_control and self.mode in ('hybrid', 'adaptive'):
                shares = [window_cpu[n] + 1e-9 for n in window_cpu]
                J = jains_index(shares)
                s_rate = len(starving_tasks) / max(1, len(tasks))
                L95 = p95(recent_lat)
                # Controller sees a noisy fairness estimate (Eq. 3): J_hat = J + xi.
                J_obs = J
                if self.meas_noise:
                    J_obs = max(0.0, min(1.0, J + self.rng.gauss(0.0, self.meas_noise)))
                self._control_step(J_obs, s_rate, L95)
                if log_trajectory:
                    # Log the *true* J and S alongside the resulting bias tuple.
                    trajectory.append((now, self.alpha, self.beta, J, s_rate))
                window_cpu = {t.name: 0.0 for t in tasks}
                next_control += self.control_period_ms

        # ----- Final metrics -----
        shares = [t.cpu_time for t in tasks]
        J = jains_index(shares) if sum(shares) else 1.0
        s_rate = len(starving_tasks) / max(1, len(tasks))
        total_cpu = sum(shares) or 1.0
        result = {
            "p95_latency": p95(lat_interactive) if lat_interactive else p95(lat_samples),
            "p95_latency_all": p95(lat_samples),
            "p95_latency_interactive": p95(lat_interactive) if lat_interactive else 0.0,
            "p95_latency_background": p95(lat_background) if lat_background else 0.0,
            "p99_latency": p99(lat_interactive) if lat_interactive else p99(lat_samples),
            "fairness_jain": J,
            "starvation_rate": s_rate,
            "alpha": self.alpha,
            "beta": self.beta,
            "sched_counts": {t.name: t.cpu_time for t in tasks},
            "cpu_shares": {t.name: t.cpu_time / total_cpu for t in tasks},
        }
        if log_trajectory:
            result["trajectory"] = trajectory
        return result

    def _control_step(self, J, s_rate, L95):
        """Algorithm 1 Phase 3 (damp / promote), gated by Sec IV-F law.

        Damp toward CFS when the fairness floor or starvation cap is breached;
        promote (cut latency) only when fairness has margin *and* latency still
        exceeds the target. All iterates are projected onto the Table I safe box
        C = [alpha_min, alpha_max] x [beta_min, beta_max], which -- together with
        the aging guardrail bounding S -- is the boundedness assumption (A1)
        underpinning the mean-square stability result of Theorem 1.
        """
        if J < self.j_min or s_rate > self.starvation_cap:
            # Damp: restore fairness.
            self.alpha = max(ALPHA_MIN, self.alpha - self.delta_a)
            self.beta = max(BETA_MIN, self.beta - self.delta_b)
        elif J > self.j_max and L95 > self.latency_target_ms:
            # Promote: cut latency.
            self.alpha = min(ALPHA_MAX, self.alpha + self.delta_a)
            self.beta = min(BETA_MAX, self.beta + self.delta_b)
        elif self.mode == 'adaptive':
            # Sec IV-F proportional law (no L95 gate): alpha_t as a function of J.
            if J > self.j_max:
                self.alpha = ALPHA_MAX
            else:
                self.alpha = ALPHA_MIN + (1.0 - J) * (ALPHA_MAX - ALPHA_MIN)
                self.alpha = max(ALPHA_MIN, min(ALPHA_MAX, self.alpha))
