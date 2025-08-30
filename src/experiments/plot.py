#!/usr/bin/env python3
import sys, csv, os, argparse, math
from pathlib import Path
from collections import defaultdict
import statistics

import matplotlib
# Default to a non-interactive backend; we'll only show() if --show
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _norm(row, keys, default=""):
    for k in keys:
        if k in row and row[k] not in ("", None):
            return row[k]
    return default

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def read_rows_one(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = _norm(row, ["algorithm","algo"])
            heur = _norm(row, ["heuristic"], "")
            depth = _to_int(_norm(row, ["depth"]))
            expanded = _to_int(_norm(row, ["expanded"]))
            generated = _to_int(_norm(row, ["generated"]))
            duplicates = _to_int(_norm(row, ["duplicates"]))
            time_sec = _to_float(_norm(row, ["time_sec","time"]))
            if algo and depth is not None:
                rows.append({
                    "algo": algo,
                    "heuristic": heur,
                    "depth": depth,
                    "expanded": expanded,
                    "generated": generated,
                    "duplicates": duplicates,
                    "time_sec": time_sec,
                })
    return rows

def read_rows(paths):
    out = []
    for p in paths:
        out.extend(read_rows_one(p))
    return out

def agg_mean(rows, metric):
    buckets = defaultdict(list)  # (algo,heur) -> [(depth,val)]
    for r in rows:
        v = r.get(metric)
        if v is None: 
            continue
        buckets[(r["algo"], r["heuristic"])].append((r["depth"], v))
    series = {}
    for key, pairs in buckets.items():
        by_depth = defaultdict(list)
        for d, v in pairs:
            by_depth[d].append(v)
        xs = sorted(by_depth.keys())
        ys = [statistics.mean(by_depth[d]) for d in xs]
        es = [statistics.pstdev(by_depth[d]) if len(by_depth[d]) > 1 else 0.0 for d in xs]
        series[key] = (xs, ys, es)
    return series

def plot_metric(ax, rows, metric):
    series = agg_mean(rows, metric)
    for (algo, heur), (xs, ys, es) in sorted(series.items()):
        # offset IDA* a tiny bit so curves don’t overlap
        offset = -0.12 if "A*" in algo else (0.12 if "IDA*" in algo else 0.0)
        xs_off = [x + offset for x in xs]
        label = f"{algo} | {heur or '—'}"
        ax.errorbar(xs_off, ys, yerr=es, marker="o", capsize=3, label=label)
    ax.set_xlabel("Depth")
    ax.set_ylabel(metric)
    ax.set_title(f"{metric} vs Depth (mean ± std)")
    ax.grid(True)
    ax.legend()

def save_fig(fig, outdir: Path, name: str):
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"Saved: {path}")

def main():
    ap = argparse.ArgumentParser(description="Plot results CSVs and save PNGs.")
    ap.add_argument("csv", nargs="+", help="One or more CSV result files")
    ap.add_argument("--save", default="results/plots", help="Directory to save plots")
    ap.add_argument("--show", action="store_true", help="Also open interactive windows (if GUI available)")
    args = ap.parse_args()

    rows = read_rows(args.csv)
    if not rows:
        print("No rows to plot. Are your CSVs empty?")
        sys.exit(0)

    outdir = Path(args.save)
    base = "combo" if len(args.csv) > 1 else Path(args.csv[0]).stem

    # Combined 3-panel figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, metric in zip(axes, ["expanded","generated","time_sec"]):
        plot_metric(ax, rows, metric)
    plt.tight_layout()
    save_fig(fig, outdir, f"{base}_combined")

    # Separate single-panel figures
    for metric in ["expanded","generated","duplicates","time_sec"]:
        fig, ax = plt.subplots(figsize=(8, 6))
        plot_metric(ax, rows, metric)
        plt.tight_layout()
        save_fig(fig, outdir, f"{base}_{metric}")
        plt.close(fig)

    if args.show:
        # Only show if user asked for it
        plt.show()

if __name__ == "__main__":
    main()
