import math, random, statistics
from .metrics import p95, jains_index

class SchedulerSim:
    def __init__(self, alpha=0.20, beta=0.15, mode='hybrid', j_min=0.96, starvation_cap=0.02, seed=42):
        self.alpha = alpha
        self.beta = beta
        self.mode = mode
        self.j_min = j_min
        self.starvation_cap = starvation_cap
        self.rng = random.Random(seed)

    def interactivity_score(self, task):
        # 0..1 based on sleep_ratio and recent_wakeup flags
        base = 0.6 * task.sleep_ratio + 0.4 * (1.0 if task.recent_wakeup else 0.0)
        return max(0.0, min(1.0, base))

    def run(self, tasks, steps=10000):
        # Simple discrete-time simulation of scheduling
        # Each step picks next task using biased vruntime + tie-breaker
        # Collects latency samples and per-task CPU shares for fairness
        time = 0
        lat_samples = []
        sched_counts = {t.name:0 for t in tasks}
        waits = {t.name:0 for t in tasks}
        starvation_events = 0

        # initialize virtual runtimes
        for t in tasks:
            t.v = 0.0

        for step in range(steps):
            # age / bias vruntime
            for t in tasks:
                B = self.interactivity_score(t)
                # bounded bias: v += dt*(1 + alpha*B)
                dt = t.quantum
                t.v += dt * (1.0 + self.alpha * B)

            # pick next task (argmin of v - beta*B)
            scored = []
            for t in tasks:
                B = self.interactivity_score(t)
                scored.append((t.v - self.beta * B, t))
            scored.sort(key=lambda x: x[0])
            _, chosen = scored[0]

            # emulate latency: lower v tends to run sooner; jitter from load
            latency = max(0.0, self.rng.lognormvariate(0.0, 0.25) * (1.0 + (chosen.v / (1e-6 + sum(tt.v for tt in tasks))) ))
            lat_samples.append(latency)

            # update bookkeeping
            for t in tasks:
                if t is chosen:
                    sched_counts[t.name] += 1
                    t.recent_wakeup = False
                else:
                    waits[t.name] += 1
                    if waits[t.name] > int(1.0 / max(1e-6, t.share) * 10):
                        starvation_events += 1
                        waits[t.name] = 0

            # hybrid control every N steps: dampen if fairness low or starvation high
            if self.mode in ('hybrid','adaptive') and (step % 200 == 0 and step > 0):
                # compute fairness on recent window
                shares = [sched_counts[n] + 1 for n in sched_counts]
                J = jains_index(shares)
                s_rate = starvation_events / (step+1)
                if J < self.j_min or s_rate > self.starvation_cap:
                    self.alpha = max(0.05, self.alpha - 0.02)
                    self.beta = max(0.05, self.beta - 0.02)
                else:
                    # gently increase if latency p95 worse than a target percentile
                    if p95(lat_samples[-500:]) > p95(lat_samples[:500] if len(lat_samples) > 500 else lat_samples) * 0.9:
                        self.alpha = min(0.35, self.alpha + 0.01)

        # metrics
        shares = [sched_counts[n] for n in sched_counts]
        J = jains_index(shares) if sum(shares) else 1.0
        s_rate = starvation_events / max(1, steps)
        return {
            "p95_latency": p95(lat_samples),
            "fairness_jain": J,
            "starvation_rate": s_rate,
            "alpha": self.alpha,
            "beta": self.beta,
            "sched_counts": sched_counts,
        }

class Task:
    def __init__(self, name, quantum=1.0, sleep_ratio=0.0, recent_wakeup=False, share=0.1):
        self.name = name
        self.quantum = quantum
        self.sleep_ratio = sleep_ratio
        self.recent_wakeup = recent_wakeup
        self.share = share
        self.v = 0.0
