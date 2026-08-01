"""Aggregate benchmark CSVs into a summary report.

For each results/<workload>.csv (written by benchmarks/_common.py) this
computes, per policy, the mean interactive-class P95 (the paper's headline
tail-latency metric), the all-task and background P95, fairness (Jain), and
starvation. It also reports BRS's P95 reduction relative to the CFS baseline
and flags whether the fairness floor (J >= 0.96) held -- mirroring the
quantities reported in Section V.
"""

import os, sys, csv, json, glob
from statistics import mean

# Fields emitted by the benchmark harness; any subset may be present.
NUMERIC_FIELDS = [
    "p95_latency", "p95_latency_all", "p95_latency_interactive",
    "p95_latency_background", "p99_latency", "fairness_jain",
    "starvation_rate", "alpha", "beta",
]


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in list(r.keys()):
                try:
                    r[k] = float(r[k])
                except (ValueError, TypeError):
                    pass
            rows.append(r)
    return rows


def _mean_field(rows, field):
    vals = [r[field] for r in rows if isinstance(r.get(field), (int, float))]
    return mean(vals) if vals else None


def summarize(rows):
    policies = {r["policy"] for r in rows}
    summary = {}
    for p in sorted(policies):
        pr = [r for r in rows if r["policy"] == p]
        summary[p] = {f: _mean_field(pr, f) for f in NUMERIC_FIELDS}

    # Headline: BRS interactive-P95 reduction vs the CFS baseline.
    if "cfs" in summary and "brs" in summary:
        cfs_p95 = summary["cfs"].get("p95_latency")
        brs_p95 = summary["brs"].get("p95_latency")
        if cfs_p95 and brs_p95 is not None and cfs_p95 > 0:
            summary["_brs_vs_cfs"] = {
                "p95_reduction_pct": round(100.0 * (cfs_p95 - brs_p95) / cfs_p95, 2),
                "fairness_floor_ok": bool(summary["brs"].get("fairness_jain", 0) >= 0.96),
            }
    return summary


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Summarize BRS benchmark CSVs.")
    ap.add_argument("--input", default="results")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(args.input, "*.csv"))
                   if os.path.basename(f) != "adversarial.csv")
    if not files:
        print("No workload CSVs found in", args.input)
        sys.exit(1)

    report = {}
    for f in files:
        rows = load_csv(f)
        if rows and "policy" in rows[0]:
            report[os.path.basename(f)] = summarize(rows)

    print(json.dumps(report, indent=2))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as g:
            json.dump(report, g, indent=2)
        print("Wrote", args.out)


if __name__ == "__main__":
    main()
