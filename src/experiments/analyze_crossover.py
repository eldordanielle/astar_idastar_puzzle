#!/usr/bin/env python3
import argparse, csv, statistics
from pathlib import Path
from collections import defaultdict
import os

import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def read_results(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = row.get("algorithm") or row.get("algo") or ""
            depth = _to_int(row.get("depth"))
            time_sec = _to_float(row.get("time_sec") or row.get("time"))
            if algo and depth is not None and time_sec is not None:
                rows.append((algo, depth, time_sec))
    return rows

def mean_time_by_algo_depth(rows):
    agg = defaultdict(list)  # (algo, depth) -> [times]
    for algo, depth, t in rows:
        agg[(algo, depth)].append(t)
    out = {}
    for (algo, depth), vals in agg.items():
        out[(algo, depth)] = statistics.mean(vals)
    return out

def compute_ratio_table(means):
    depths = sorted({d for (_, d) in means.keys()})
    table = []
    for d in depths:
        a = means.get(("A*", d))
        i = means.get(("IDA*", d))
        if a is not None and i is not None and a > 0:
            table.append((d, i / a))
    return table  # list of (depth, ratio)

# def find_crossover(table):
#     """First depth where ratio <= 1 (IDA* <= A*). Returns (depth, ratio) or None."""
#     for d, r in sorted(table):
#         if r <= 1.0:
#             return (d, r)
#     return None

def first_flip_crossing(table):
    """Return the first depth where the curve crosses from >1 to <=1 (IDA* becomes faster),
    or from <=1 to >1 (IDA* becomes slower). Returns (depth, ratio, direction) or None.
    direction is 'down' for A*->IDA* (good for IDA*), 'up' for IDA*->A*."""
    if not table:
        return None
    # sort by depth
    table = sorted(table)
    prev_d, prev_r = table[0]
    for d, r in table[1:]:
        if prev_r > 1.0 and r <= 1.0:
            return (d, r, "down")
        if prev_r <= 1.0 and r > 1.0:
            return (d, r, "up")
        prev_d, prev_r = d, r
    return None

def find_crossover(table):
    """Deprecated: kept for backward compat in case other code calls it."""
    return first_flip_crossing(table)

def plot_ratio(curves, outdir, name, show=False):
    plt.figure(figsize=(7.5,5))
    for label, table in curves:
        xs = [d for d,_ in sorted(table)]
        ys = [r for _,r in sorted(table)]
        plt.plot(xs, ys, marker="o", label=label)

        # cross = find_crossover(table)
        # if cross:
        #     plt.axvline(cross[0], linestyle="--")
        #     plt.text(cross[0], min(ys), f" crossover @ {cross[0]}", rotation=90, va="bottom")
        
        cross = first_flip_crossing(table)
        if cross:
            x, y, direction = cross
            plt.axvline(x, linestyle="--")
            txt = " IDA* becomes faster" if direction == "down" else " A* becomes faster"
            plt.text(x, min(ys), f" crossover @ {x}{txt}", rotation=90, va="bottom")

    plt.axhline(1.0, color="gray", linestyle=":")
    plt.xlabel("Depth")
    plt.ylabel("IDA*/A* time ratio")
    plt.title("Crossover of IDA* vs A* (ratio < 1 means IDA* faster)")
    plt.grid(True)
    plt.legend()
    outdir.mkdir(parents=True, exist_ok=True)
    of = outdir / f"{name}_crossover.png"
    plt.savefig(of, dpi=200, bbox_inches="tight")
    print(f"Saved: {of}")
    if show:
        plt.show()

def main():
    ap = argparse.ArgumentParser(description="Analyze crossover (IDA*/A* time ratio) for one or more CSVs.")
    ap.add_argument("files", nargs="+", help="result CSVs produced by runner.py")
    ap.add_argument("--save", default="results/plots")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    curves = []
    for f in args.files:
        rows = read_results(f)
        means = mean_time_by_algo_depth(rows)
        table = compute_ratio_table(means)
        label = Path(f).stem
        curves.append((label, table))

        # Console table
        print(f"\n== {label} ==")
        print("Depth  Ratio(IDA*/A*)")
        for d, r in sorted(table):
            print(f"{d:>5}  {r:8.3f}")
        cross = find_crossover(table)
        if cross:
            print(f"-> crossover around depth {cross[0]} (ratio={cross[1]:.3f})")
        else:
            print("-> no crossover within these depths")

    plot_ratio(curves, Path(args.save), "crossover", show=args.show)

if __name__ == "__main__":
    main()
