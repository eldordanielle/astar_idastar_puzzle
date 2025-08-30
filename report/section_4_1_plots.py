#!/usr/bin/env python3
"""
Section 4.1 figures: per-depth grids (A*, IDA*, IDA*+BPMX)
- One figure per board: Manhattan row and Linear Conflict row
- Columns: expanded / generated / time_sec
- Reads results/*_{manhattan|linear}_{plain|bpmx}.csv
- Saves to report/figs/4_1/grid_full_<board>.png
"""

import csv, math, statistics
from collections import defaultdict
from pathlib import Path
import os

import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

OUTDIR = Path("report/figs/4_1")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Boards and nice labels
BOARDS = [
    ("p8",   "P 8"),
    ("p15",  "P 15"),
    ("r3x4", "R 3×4"),
    ("r3x5", "R 3×5"),
]

# Heuristic file-key -> display name
HEURS = [("manhattan", "Manhattan"), ("linear", "Linear Conflict")]

# Metrics we plot as columns
METRICS = [("expanded", "expanded"), ("generated", "generated"), ("time_sec", "seconds")]

# Colors / styles (color-blind friendly)
COL_A   = "#1f77b4"  # A*
COL_IDA = "#ff7f0e"  # IDA*
COL_BPX = "#2ca02c"  # IDA*+BPMX

def _norm(row, keys, default=""):
    for k in keys:
        if k in row and row[k] != "":
            return row[k]
    return default

def load_csv(path):
    """Tolerant loader. Returns list of dicts with normalized fields."""
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = _norm(row, ["algorithm","algo"])
            if not algo:
                continue
            depth = _norm(row, ["depth"])
            expd  = _norm(row, ["expanded"])
            gen   = _norm(row, ["generated"])
            time  = _norm(row, ["time_sec","time"])
            try: depth = int(depth)
            except: depth = None
            try: expd = int(expd)
            except: expd = None
            try: gen  = int(gen)
            except: gen  = None
            try: time = float(time)
            except: time = None
            rows.append({"algo": algo, "depth": depth, "expanded": expd, "generated": gen, "time_sec": time})
    return rows

def group_by_algo_depth(rows):
    """depth -> algo -> metric -> list[vals]"""
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for r in rows:
        if r["depth"] is None: 
            continue
        for m in ("expanded","generated","time_sec"):
            if r[m] is not None:
                agg[r["depth"]][r["algo"]][m].append(r[m])
    return agg

def mean_sem(vals):
    if not vals:
        return (math.nan, math.nan)
    if len(vals) == 1:
        return (vals[0], math.nan)
    m = statistics.mean(vals)
    s = statistics.stdev(vals)
    return (m, s / math.sqrt(len(vals)))

def build_panel(ax, depths_sorted, series, metric, ylabel=None, title=None):
    """
    series: dict with keys 'A*','IDA*','IDA* (BPMX ON)' mapping to depth->(mean,sem)
    """
    # Prepare x, y, yerr per algo
    lines = [
        ("A*",              COL_A,   "-", 1.8),
        ("IDA*",            COL_IDA, "-", 1.8),
        ("IDA* (BPMX ON)",  COL_BPX, "--", 2.2),
    ]
    for name, color, ls, lw in lines:
        ys, es, xs = [], [], []
        for d in depths_sorted:
            if d in series[name]:
                m, e = series[name][d]
                xs.append(d); ys.append(m); es.append(e)
        if xs:
            ax.errorbar(xs, ys, yerr=es, marker="o", lw=lw, color=color, ls=ls, capsize=2, alpha=0.95, label=name)

    ax.set_xlabel("Depth")
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, pad=6, fontsize=10)
    ax.grid(True, alpha=0.15, linestyle=":")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    # nicer y tick formatting for time
    if metric == "time_sec":
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)

def plot_board(board_key, board_label):
    fig, axes = plt.subplots(2, 3, figsize=(10, 10))
    fig.suptitle(f"{board_label} — per-depth (Manhattan vs Linear Conflict)", fontsize=16, y=0.98)

    for row_idx, (heur_key, heur_label) in enumerate(HEURS):
        # files
        plain_path = Path(f"results/{board_key}_{heur_key}_plain.csv")
        bpmx_path  = Path(f"results/{board_key}_{heur_key}_bpmx.csv")
        if not (plain_path.exists() and bpmx_path.exists()):
            print(f"skip {board_key}/{heur_key}: missing {plain_path.name or bpmx_path.name}")
            # still draw empty axes with a note
            for col_idx in range(3):
                axes[row_idx, col_idx].text(0.5, 0.5, "missing data", ha="center", va="center")
                axes[row_idx, col_idx].axis("off")
            continue

        plain = load_csv(plain_path)
        bpmx  = load_csv(bpmx_path)

        # aggregate by depth+algo
        agg_plain = group_by_algo_depth(plain)  # depth -> algo -> metric -> list
        agg_bpmx  = group_by_algo_depth(bpmx)

        # depths present
        depths = sorted(set(agg_plain.keys()) | set(agg_bpmx.keys()))
        if depths and (depths[0] > 4 or depths[-1] < 20):
            print(f"coverage {board_key}/{heur_key}: depths={depths}")

        # build per-metric series (algo -> depth -> (mean,sem))
        series_by_metric = {m:{} for m,_ in METRICS}
        algos = ("A*","IDA*","IDA* (BPMX ON)")
        for m,_ in METRICS:
            series = {a:{} for a in algos}
            for d in depths:
                # A* & IDA* come from plain file, BPMX from bpmx file
                for a in ("A*","IDA*"):
                    vals = agg_plain.get(d, {}).get(a, {}).get(m, [])
                    if vals: series[a][d] = mean_sem(vals)
                a = "IDA* (BPMX ON)"
                vals = agg_bpmx.get(d, {}).get(a, {}).get(m, [])
                if vals: series[a][d] = mean_sem(vals)
            series_by_metric[m] = series

        # draw the row
        for col_idx, (metric, ylab) in enumerate(METRICS):
            ax = axes[row_idx, col_idx]
            title = heur_label if col_idx == 0 else None
            build_panel(ax, depths, series_by_metric[metric], metric, ylabel=ylab if col_idx==0 else None, title=title)

    # one legend at the top center
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.95), fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = OUTDIR / f"grid_full_{board_key}.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"✅ {out}")

def main():
    for key, label in BOARDS:
        plot_board(key, label)

if __name__ == "__main__":
    main()
