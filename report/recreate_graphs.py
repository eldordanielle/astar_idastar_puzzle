#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGS = Path("report/figs"); FIGS.mkdir(parents=True, exist_ok=True)

# Taller layout (title above)
FIGSIZE = (16, 8.6)
GRID = dict(left=0.06, right=0.985, bottom=0.12, top=0.86, wspace=0.28)
TITLE_Y, LEGEND_Y = 0.975, 0.91

COLORS = {
    "A*":        "#0072B2",  # blue
    "IDA*":      "#E69F00",  # orange
    "IDA*+BPMX": "#009E73",  # bluish green
}
STYLES = {
    "A*":        dict(color=COLORS["A*"], marker="o", lw=2.4, ms=6, ls="-"),
    "IDA*":      dict(color=COLORS["IDA*"], marker="s", lw=2.4, ms=6, ls="-"),
    "IDA*+BPMX": dict(color=COLORS["IDA*+BPMX"], marker="^", lw=2.6, ms=6, ls="--"),
}
plt.rcParams.update({"font.size": 13, "axes.titlesize": 16, "axes.labelsize": 14,
                     "xtick.labelsize": 12, "ytick.labelsize": 12})

EVEN_DEPTHS = list(range(4, 21, 2))

def load_ok(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok") == "ok"]
    return df

def aggregate(df: pd.DataFrame, metrics=("expanded","generated","time_sec")) -> pd.DataFrame:
    keep = ["algorithm","depth",*metrics]
    df = df[[c for c in keep if c in df.columns]].copy()
    def sem(x):
        n = max(1, np.sum(~np.isnan(x)))
        return np.nanstd(x, ddof=1)/math.sqrt(n) if n>1 else 0.0
    out = (df.groupby(["algorithm","depth"], as_index=False)
             .agg({m:["mean",sem] for m in metrics}))
    out.columns = ["algorithm","depth"] + [f"{m}_{k}" for m in metrics for k in ("mean","sem")]
    return out.sort_values(["algorithm","depth"])

def add_series(ax, data, label):
    ax.errorbar(data["depth"], data["value"], yerr=data["sem"],
                capsize=3, elinewidth=1.2, **STYLES[label])

def layout(title):
    fig = plt.figure(figsize=FIGSIZE, constrained_layout=False)
    gs = fig.add_gridspec(1, 3, **GRID)
    ax1 = fig.add_subplot(gs[0,0]); ax2 = fig.add_subplot(gs[0,1]); ax3 = fig.add_subplot(gs[0,2])
    fig.suptitle(title, fontsize=24, fontweight="bold", y=TITLE_Y)
    return fig, (ax1,ax2,ax3)

def finalize(ax, ylab):
    ax.set_xlabel("Depth"); ax.set_ylabel(ylab); ax.grid(True, alpha=0.25, linestyle=":")
    ax.set_xticks(EVEN_DEPTHS); ax.set_xlim(4,20)

def legend(fig, labels_present):
    order = ["A*","IDA*","IDA*+BPMX"]
    labs = [l for l in order if l in labels_present]
    handles = [plt.Line2D([0],[0], **STYLES[l], label=l) for l in labs]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.91),
               ncol=len(labs), frameon=False)

def make_plot(board_name: str, heur_label: str, csv_main: Path,
              csv_ida_plain: Path, csv_ida_bpmx: Path, out_png: Path):
    df_main = aggregate(load_ok(csv_main))
    bpmx_df = None
    if csv_ida_plain.exists() and csv_ida_bpmx.exists():
        ida_plain = aggregate(load_ok(csv_ida_plain))
        ida_bpmx  = aggregate(load_ok(csv_ida_bpmx))
        # ensure both share the same depth grid (4..20 evens) for overlay
        common = sorted(set(ida_plain["depth"]).intersection(set(ida_bpmx["depth"])))
        bpmx_df = ida_bpmx[ida_bpmx["depth"].isin(common)].copy()
        bpmx_df["algorithm"] = "IDA*+BPMX"

    fig, (ax1,ax2,ax3) = layout(f"{board_name} ({heur_label}) — per-depth curves")
    labels = set()

    def draw(ax, metric, ylab):
        if not df_main[df_main["algorithm"]=="A*"].empty:
            a = df_main[df_main["algorithm"]=="A*"][["depth", f"{metric}_mean", f"{metric}_sem"]]
            a.columns = ["depth","value","sem"]; add_series(ax, a, "A*"); labels.add("A*")
        if not df_main[df_main["algorithm"]=="IDA*"].empty:
            i = df_main[df_main["algorithm"]=="IDA*"][["depth", f"{metric}_mean", f"{metric}_sem"]]
            i.columns = ["depth","value","sem"]; add_series(ax, i, "IDA*"); labels.add("IDA*")
        if bpmx_df is not None and not bpmx_df.empty:
            b = bpmx_df[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
            b.columns = ["depth","value","sem"]; add_series(ax, b, "IDA*+BPMX"); labels.add("IDA*+BPMX")
        finalize(ax, ylab)

    draw(ax1, "expanded", "expanded")
    draw(ax2, "generated", "generated")
    draw(ax3, "time_sec", "seconds")
    legend(fig, labels)
    fig.savefig(out_png, dpi=200); plt.close(fig); print("✅", out_png)

def exists(p: Path) -> bool:
    try: return p.exists()
    except: return False

def main():
    jobs = [
        # (board title, heur short, main merged, ida_plain, ida_bpmx, out png)
        ("8-puzzle", "Manhattan",
         Path("results/p8_manhattan.csv"),
         Path("results/p8_ida_manhattan_plain.csv"),
         Path("results/p8_ida_manhattan_bpmx.csv"),
         FIGS/"p8_manhattan_full_combined.png"),

        ("8-puzzle", "Linear Conflict",
         Path("results/p8_linear_conflict.csv"),
         Path("results/p8_ida_linear_conflict_plain.csv"),
         Path("results/p8_ida_linear_conflict_bpmx.csv"),
         FIGS/"p8_linear_full_combined.png"),

        ("15-puzzle", "Manhattan",
         Path("results/p15_manhattan.csv"),
         Path("results/p15_ida_manhattan_plain.csv"),
         Path("results/p15_ida_manhattan_bpmx.csv"),
         FIGS/"p15_manhattan_full_combined.png"),

        ("15-puzzle", "Linear Conflict",
         Path("results/p15_linear_conflict.csv"),
         Path("results/p15_ida_linear_conflict_plain.csv"),
         Path("results/p15_ida_linear_conflict_bpmx.csv"),
         FIGS/"p15_linear_full_combined.png"),

        ("R 3×4", "Manhattan",
         Path("results/r3x4_manhattan.csv"),
         Path("results/r3x4_ida_manhattan_plain.csv"),
         Path("results/r3x4_ida_manhattan_bpmx.csv"),
         FIGS/"r3x4_manhattan_full_combined.png"),

        ("R 3×4", "Linear Conflict",
         Path("results/r3x4_linear_conflict.csv"),
         Path("results/r3x4_ida_linear_conflict_plain.csv"),
         Path("results/r3x4_ida_linear_conflict_bpmx.csv"),
         FIGS/"r3x4_linear_full_combined.png"),

        ("R 3×5", "Manhattan",
         Path("results/r3x5_manhattan.csv"),
         Path("results/r3x5_ida_manhattan_plain.csv"),
         Path("results/r3x5_ida_manhattan_bpmx.csv"),
         FIGS/"r3x5_manhattan_full_combined.png"),

        ("R 3×5", "Linear Conflict",
         Path("results/r3x5_linear_conflict.csv"),
         Path("results/r3x5_ida_linear_conflict_plain.csv"),
         Path("results/r3x5_ida_linear_conflict_bpmx.csv"),
         FIGS/"r3x5_linear_full_combined.png"),
    ]
    for job in jobs:
        # allow missing files gracefully; make only what we can
        _,_, main_csv, ida_plain, ida_bpmx, out = job
        if not exists(main_csv): 
            print("skip:", out, "(missing", main_csv, ")"); continue
        make_plot(*job)

if __name__ == "__main__":
    main()
