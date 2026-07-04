"""
Interactivity score B_i as defined in the BRS paper, Section IV-C.

B_i is a bounded, normalized combination of three per-task signals measured over
a sliding window of the most recent W scheduling events (default W = 64):

  * sleep ratio          s_i = T_sleep / (T_sleep + T_run)          in [0, 1]
  * I/O-wait ratio       w_i = T_iowait / (T_sleep + T_run)         in [0, 1]
  * scheduling-history   h_i = min(1, n_wake / n_wake_ref)          in [0, 1]

The instantaneous score is the convex combination

    B~_i = lambda1 * s_i + lambda2 * w_i + lambda3 * h_i,
    lambda1 + lambda2 + lambda3 = 1   (defaults 0.5, 0.3, 0.2)

so B~_i lies in [0, 1] by construction. To prevent transient behaviour from
causing abrupt re-prioritisation, the score actually used by Eq. (2) is an
exponentially weighted moving average

    B_i <- (1 - rho) * B_i + rho * B~_i,   rho = 0.25.

All three raw signals mirror quantities the kernel already maintains
(se.statistics, task_struct I/O accounting); here they are estimated from a
per-task sliding window so the simulator computes B_i in O(1) per update with
no new data structures, exactly as the paper describes.
"""

from collections import deque

# Defaults from Section IV-C / Table-adjacent text.
LAMBDA1_SLEEP = 0.5
LAMBDA2_IOWAIT = 0.3
LAMBDA3_HISTORY = 0.2
DEFAULT_WINDOW = 64          # W: recent scheduling events
DEFAULT_RHO = 0.25           # EWMA smoothing factor
DEFAULT_NWAKE_REF_HZ = 50.0  # n_wake_ref reference wake-up rate (Hz)

assert abs((LAMBDA1_SLEEP + LAMBDA2_IOWAIT + LAMBDA3_HISTORY) - 1.0) < 1e-9


class InteractivityEstimator:
    """Sliding-window estimator of B_i with EWMA smoothing.

    The estimator is fed raw per-event observations (how long the task slept,
    how much of that was I/O wait, whether the event was a wake-up) and returns
    the smoothed, bounded score used by the vruntime update.
    """

    def __init__(self, window=DEFAULT_WINDOW, rho=DEFAULT_RHO,
                 nwake_ref_hz=DEFAULT_NWAKE_REF_HZ,
                 l1=LAMBDA1_SLEEP, l2=LAMBDA2_IOWAIT, l3=LAMBDA3_HISTORY):
        self.window = window
        self.rho = rho
        self.nwake_ref_hz = nwake_ref_hz
        self.l1, self.l2, self.l3 = l1, l2, l3
        # Ring buffers over the last W scheduling events.
        self._sleep = deque(maxlen=window)   # T_sleep per event
        self._run = deque(maxlen=window)     # T_run per event
        self._iowait = deque(maxlen=window)  # T_iowait per event
        self._wakes = deque(maxlen=window)   # 1 if the event was a wake-up
        self.B = 0.0                         # EWMA-smoothed score in [0, 1]

    def observe(self, t_sleep, t_run, t_iowait=0.0, woke=False):
        """Record one scheduling event and update the smoothed score."""
        self._sleep.append(max(0.0, t_sleep))
        self._run.append(max(0.0, t_run))
        self._iowait.append(max(0.0, min(t_iowait, t_sleep)))
        self._wakes.append(1.0 if woke else 0.0)
        self._update()
        return self.B

    def _update(self):
        total = sum(self._sleep) + sum(self._run)
        if total <= 0.0:
            b_inst = 0.0
        else:
            s_i = sum(self._sleep) / total
            w_i = sum(self._iowait) / total
            # Wake-up frequency over the window, normalised by the reference
            # rate. The window spans `total` units of (simulated) wall time.
            n_wake = sum(self._wakes)
            wake_rate = n_wake / total if total > 0 else 0.0
            h_i = min(1.0, wake_rate / self.nwake_ref_hz) if self.nwake_ref_hz > 0 else 0.0
            b_inst = self.l1 * s_i + self.l2 * w_i + self.l3 * h_i
            b_inst = max(0.0, min(1.0, b_inst))  # bounded by construction
        # EWMA smoothing (Section IV-C).
        self.B = (1.0 - self.rho) * self.B + self.rho * b_inst
        # Numerical guard: keep strictly within [0, 1].
        self.B = max(0.0, min(1.0, self.B))

    @property
    def score(self):
        return self.B
