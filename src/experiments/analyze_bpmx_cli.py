#!/usr/bin/env python3
import argparse, csv, statistics
from collections import defaultdict
from pathlib import Path
import os
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = row.get("algorithm") or row.get("algo") or ""
            if not algo: continue
            depth = int(row["depth"])
            expanded = int(row["expanded"])
            generated = int(row["generated"])
            time_sec = float(row.get("time_sec") or row.get("time") or 0.0)
            rows.append((algo, depth, expanded, generated, time_sec))
    return rows

def mean_by_depth(rows, algo_name):
    agg = defaultdict(lambda: defaultdict(list))  # depth -> metric -> vals
    for algo, d, expd, gen, t in rows:
        if algo == algo_name:
            agg[d]["exp"].append(expd)
            agg[d]["gen"].append(gen)
            agg[d]["time"].append(t)
    out = {}
    for d, buckets in agg.items():
        out[d] = {k: statistics.mean(v) for k, v in buckets.items()}
    return out  # {depth: {"exp":..., "gen":..., "time":...}}

def main():
    ap = argparse.ArgumentParser(description="Analyze BPMX impact (IDA*+BPMX vs IDA*).")
    ap.add_argument("--plain", required=True, help="CSV with IDA* (plain)")
    ap.add_argument("--bpmx", required=True, help="CSV with IDA* (BPMX ON)")
    ap.add_argument("--save", default="results/plots")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    plain = mean_by_depth(load(args.plain), "IDA*")
    bpmx  = mean_by_depth(load(args.bpmx),  "IDA* (BPMX ON)")

    depths = sorted(set(plain.keys()) & set(bpmx.keys()))
    if not depths:
        print("No common depths between files.")
        return

    print("\nDepth  Expanded  ->  Ratio  |  Generated  ->  Ratio  |  Time(s)  ->  Ratio")
    for d in depths:
        p, b = plain[d], bpmx[d]
        r_exp = b["exp"]/p["exp"]
        r_gen = b["gen"]/p["gen"]
        r_tim = b["time"]/p["time"] if p["time"] > 0 else float("inf")
        print(f"{d:>5}  {p['exp']:8.1f}->{r_exp:5.2f}x | {p['gen']:9.1f}->{r_gen:5.2f}x | {p['time']:7.4f}->{r_tim:5.2f}x")

    # Small ratio plot (time only)
    xs = depths
    ys = [bpmx[d]["time"]/plain[d]["time"] for d in xs]
    plt.figure(figsize=(6,4))
    plt.plot(xs, ys, marker="o")
    plt.axhline(1.0, color="gray", linestyle=":")
    plt.xlabel("Depth")
    plt.ylabel("Time ratio (BPMX/Plain)")
    plt.title("BPMX speedup (ratio < 1 is good)")
    Path(args.save).mkdir(parents=True, exist_ok=True)
    out = Path(args.save) / "bpmx_ratio.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    print(f"\nSaved: {out}")
    if args.show:
        plt.show()

if __name__ == "__main__":
    main()
