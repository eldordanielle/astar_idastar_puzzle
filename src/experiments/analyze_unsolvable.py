#!/usr/bin/env python3
import argparse, csv, statistics, os
from collections import defaultdict
from pathlib import Path

import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                rows.append({
                    "algo": row.get("algorithm") or row.get("algo"),
                    "solvable": int(row.get("solvable", 1)),
                    "depth": int(row["depth"]),
                    "expanded": int(row.get("expanded","0") or 0),
                    "generated": int(row.get("generated","0") or 0),
                    "time": float(row.get("time_sec") or row.get("time") or 0.0),
                    "termination": row.get("termination","ok"),
                })
            except Exception:
                continue
    return rows

def mean_by_algo(rows, only_unsolvable=True):
    filt = [r for r in rows if (r["solvable"] == 0) == only_unsolvable]
    agg = defaultdict(lambda: defaultdict(list))  # algo -> metric -> vals
    for r in filt:
        agg[r["algo"]]["time"].append(r["time"])
        agg[r["algo"]]["expanded"].append(r["expanded"])
        agg[r["algo"]]["generated"].append(r["generated"])
    out = {}
    for algo, m in agg.items():
        out[algo] = {k: (statistics.mean(v) if v else 0.0) for k,v in m.items()}
    return out

def barplot(means, outdir: Path, name: str, metric: str):
    algos = sorted(means.keys())
    ys = [means[a][metric] for a in algos]
    plt.figure(figsize=(6,4))
    plt.bar(algos, ys)
    plt.ylabel(metric)
    plt.title(f"Unsolvable: mean {metric} by algorithm")
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"{name}_{metric}.png"
    plt.savefig(p, dpi=200, bbox_inches="tight")
    print(f"Saved: {p}")

def main():
    ap = argparse.ArgumentParser(description="Summarize unsolvable vs solvable performance.")
    ap.add_argument("csv", help="CSV produced by runner.py with solvable column")
    ap.add_argument("--save", default="results/plots")
    args = ap.parse_args()

    rows = load(args.csv)
    uns = mean_by_algo(rows, only_unsolvable=True)
    sol = mean_by_algo(rows, only_unsolvable=False)

    print("\n=== Unsolvable averages ===")
    for a,v in sorted(uns.items()):
        print(f"{a:8s}  time={v['time']:.6f}  expanded={v['expanded']:.1f}  generated={v['generated']:.1f}")

    print("\n=== Solvable averages ===")
    for a,v in sorted(sol.items()):
        print(f"{a:8s}  time={v['time']:.6f}  expanded={v['expanded']:.1f}  generated={v['generated']:.1f}")

    outdir = Path(args.save)
    barplot(uns, outdir, "unsolvable", "time")
    barplot(uns, outdir, "unsolvable", "expanded")
    barplot(uns, outdir, "unsolvable", "generated")

if __name__ == "__main__":
    main()
