import math, statistics

def p95(xs):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = int(0.95 * (len(xs)-1))
    return xs[k]

def jains_index(shares):
    s1 = sum(shares)
    s2 = sum(x*x for x in shares)
    if s2 == 0:
        return 1.0
    n = len(shares) if shares else 1
    return (s1*s1) / (n * s2)

def perf_per_watt(throughput, watts):
    if watts <= 0:
        return 0.0
    return throughput / watts
