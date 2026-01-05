import os, sys, csv, json, glob
from statistics import mean
from sched_brs_sim.metrics import perf_per_watt

def load_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            # convert numeric fields
            for k in list(r.keys()):
                try:
                    r[k] = float(r[k])
                except (ValueError, TypeError):
                    pass
            rows.append(r)
    return rows

def summarize(rows):
    pols = {r["policy"] for r in rows}
    s = {}
    for p in pols:
        pr = [r for r in rows if r["policy"] == p]
        s[p] = {
            "p95_latency": mean(r["p95_latency"] for r in pr),
            "fairness_jain": mean(r["fairness_jain"] for r in pr),
            "starvation_rate": mean(r["starvation_rate"] for r in pr),
            "alpha": mean(r["alpha"] for r in pr),
            "beta": mean(r["beta"] for r in pr),
        }
    return s

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=False, default=None)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.input, "*.csv")))
    if not files:
        print("No CSVs found in", args.input)
        sys.exit(1)

    report = {}
    for f in files:
        rows = load_csv(f)
        report[os.path.basename(f)] = summarize(rows)

    print(json.dumps(report, indent=2))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as g:
            json.dump(report, g, indent=2)

if __name__ == "__main__":
    main()
