#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGS = Path("report/figs")
FIGS.mkdir(parents=True, exist_ok=True)

FIGSIZE = (16, 8.4)
GRID_TOP = 0.86
GRID_BOTTOM = 0.12
GRID_LEFT = 0.06
GRID_RIGHT = 0.985
GRID_WSPACE = 0.28

TITLE_Y = 0.975
LEGEND_Y = 0.91

COLORS = {
    "A*":        "#0072B2",
    "IDA*":      "#E69F00",
    "IDA*+BPMX": "#009E73",
}

STYLES = {
    "A*":        dict(color=COLORS["A*"], marker="o", lw=2.4, ms=6, ls="-"),
    "IDA*":      dict(color=COLORS["IDA*"], marker="s", lw=2.4, ms=6, ls="-"),
    "IDA*+BPMX": dict(color=COLORS["IDA*+BPMX"], marker="^", lw=2.6, ms=6, ls="--"),
}

plt.rcParams.update({
    "font.size": 13,
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

def load_ok(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok") == "ok"]
    return df

def aggregate(df: pd.DataFrame, metrics=("expanded", "generated", "time_sec")) -> pd.DataFrame:
    keep = ["algorithm", "depth", *metrics]
    df = df[[c for c in keep if c in df.columns]].copy()

    def sem(x):
        n = max(1, np.sum(~np.isnan(x)))
        return np.nanstd(x, ddof=1) / math.sqrt(n) if n > 1 else 0.0

    out = (df
           .groupby(["algorithm", "depth"], as_index=False)
           .agg({m: ["mean", sem] for m in metrics}))
    out.columns = ["algorithm", "depth"] + [f"{m}_{k}" for m in metrics for k in ("mean","sem")]
    return out.sort_values(["algorithm", "depth"])

def add_series(ax, data: pd.DataFrame, algo_label: str, x="depth", y="value", yerr="sem"):
    ax.errorbar(
        data[x], data[y], yerr=data[yerr],
        capsize=3, elinewidth=1.3, **STYLES[algo_label]
    )

def layout_with_title_and_legend(title: str):
    fig = plt.figure(figsize=FIGSIZE, constrained_layout=False)
    gs = fig.add_gridspec(
        1, 3, left=GRID_LEFT, right=GRID_RIGHT,
        bottom=GRID_BOTTOM, top=GRID_TOP, wspace=GRID_WSPACE
    )
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    fig.suptitle(title, fontsize=24, fontweight="bold", y=TITLE_Y)
    return fig, (ax1, ax2, ax3)

def finalize_axes(ax, xlab, ylab):
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.grid(True, alpha=0.25, linestyle=":")

def put_legend(fig, labels_present):
    order = ["A*", "IDA*", "IDA*+BPMX"]
    labels = [l for l in order if l in labels_present]
    handles = [plt.Line2D([0], [0], **STYLES[l], label=l) for l in labels]
    fig.legend(handles=handles, loc="upper center",
               bbox_to_anchor=(0.5, LEGEND_Y), ncol=len(labels), frameon=False)

def make_plot(df_main: pd.DataFrame, title: str, out_path: Path,
              add_bpmx: pd.DataFrame | None = None):
    fig, (ax1, ax2, ax3) = layout_with_title_and_legend(title)
    labels_present = set()

    def plot_algo(ax, df_src, algo_name, metric):
        cur = df_src[df_src["algorithm"] == algo_name]
        if cur.empty:
            return False
        d = cur[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
        d.columns = ["depth", "value", "sem"]
        add_series(ax, d, algo_name)
        return True

    def draw_metric(ax, metric, ylab):
        if plot_algo(ax, df_main, "A*", metric): labels_present.add("A*")
        if plot_algo(ax, df_main, "IDA*", metric): labels_present.add("IDA*")
        # Prefer BPMX from main df if present; otherwise use the overlay
        plotted_bpmx = plot_algo(ax, df_main, "IDA*+BPMX", metric)
        if (not plotted_bpmx) and (add_bpmx is not None) and (not add_bpmx.empty):
            b = add_bpmx[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
            b.columns = ["depth", "value", "sem"]
            add_series(ax, b, "IDA*+BPMX")
            labels_present.add("IDA*+BPMX")
        elif plotted_bpmx:
            labels_present.add("IDA*+BPMX")
        finalize_axes(ax, "Depth", ylab)

    draw_metric(ax1, "expanded", "expanded")
    draw_metric(ax2, "generated", "generated")
    draw_metric(ax3, "time_sec", "seconds")

    put_legend(fig, labels_present)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"✅ {out_path}")

def exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False

def maybe_make_bpmx_overlay(plain_path: Path, bpmx_path: Path) -> pd.DataFrame | None:
    """Build an overlay DataFrame for IDA*+BPMX if both CSVs exist."""
    if exists(plain_path) and exists(bpmx_path):
        ida_plain = aggregate(load_ok(plain_path))
        ida_bpmx  = aggregate(load_ok(bpmx_path))
        common = sorted(set(ida_plain["depth"]).intersection(set(ida_bpmx["depth"])))
        add_b = ida_bpmx[ida_bpmx["depth"].isin(common)].copy()
        add_b["algorithm"] = "IDA*+BPMX"
        return add_b
    return None

def main():
    # 8-puzzle (Manhattan) + optional BPMX overlay
    p8 = Path("results/p8_manhattan.csv")
    p8_plain = Path("results/p8_ida_plain.csv")
    p8_bpmx  = Path("results/p8_ida_bpmx.csv")

    if exists(p8):
        df_p8 = aggregate(load_ok(p8))
        add_b8 = maybe_make_bpmx_overlay(p8_plain, p8_bpmx)
        make_plot(df_p8,
                  title="8-puzzle (Manhattan) — per-depth curves",
                  out_path=FIGS / "p8_manhattan_full_combined.png",
                  add_bpmx=add_b8)
    else:
        print("⚠️  Missing:", p8)

    # 15-puzzle (Manhattan) + optional BPMX overlay
    p15 = Path("results/p15_manhattan.csv")
    p15_plain = Path("results/p15_ida_plain.csv")
    p15_bpmx  = Path("results/p15_ida_bpmx.csv")

    if exists(p15):
        df_p15 = aggregate(load_ok(p15))
        add_b15 = maybe_make_bpmx_overlay(p15_plain, p15_bpmx)
        make_plot(df_p15,
                  title="15-puzzle (Manhattan) — per-depth curves",
                  out_path=FIGS / "p15_manhattan_full_combined.png",
                  add_bpmx=add_b15)
    else:
        print("⚠️  Missing:", p15)

if __name__ == "__main__":
    main()
