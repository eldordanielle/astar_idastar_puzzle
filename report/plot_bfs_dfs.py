#!/usr/bin/env python3
import os, glob
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("report/figs"); OUT.mkdir(parents=True, exist_ok=True)

# Boards to show in the figure (feel free to include r3x4/r3x5 too)
# BOARDS = [("p8", "P 8"), ("p15", "P 15")]
BOARDS = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]

# Okabe–Ito colors (color-blind friendly)
C_BFS = "#0072B2"   # blue
C_DFS = "#E69F00"   # orange

EXCLUDE = ("bpmx", "unsolv", "unsolvable", "astar_vs_ida", "smoke", "sanity")

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def find_files(board: str) -> list[Path]:
    pats = [
        f"results/{board}_*.csv",
        f"results/{board}*.csv",
        f"results/**/*{board}*.csv",
    ]
    out = []
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            name = os.path.basename(p).lower()
            if any(tag in name for tag in EXCLUDE):
                continue
            out.append(Path(p))
    # stable order, unique
    seen, uniq = set(), []
    for p in sorted(out):
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def load_board(board: str) -> pd.DataFrame | None:
    files = find_files(board)
    if not files:
        return None
    dfs = []
    for p in files:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        need = {"algorithm", "depth", "time_sec"}
        if not need.issubset(df.columns):
            continue
        if "termination" in df.columns:
            df = df[df["termination"].fillna("ok") == "ok"]
        # keep only BFS/DFS rows
        df = df[df["algorithm"].isin(["BFS", "DFS"])].copy()
        if df.empty:
            continue
        # some runs may miss expanded; fill with NaN so we can still plot time
        for c in ("expanded",):
            if c not in df.columns:
                df[c] = np.nan
        dfs.append(df)
    if not dfs:
        return None
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    return df

def agg_curves(df: pd.DataFrame, algo: str) -> pd.DataFrame:
    part = df[df["algorithm"] == algo]
    if part.empty:
        return pd.DataFrame(columns=["depth","time_mean","time_sem","exp_mean","exp_sem","n"])
    g = (part.groupby("depth", as_index=False)
               .agg(time_mean=("time_sec", "mean"),
                    time_sem =("time_sec", sem),
                    exp_mean =("expanded", "mean"),
                    exp_sem  =("expanded", sem),
                    n=("time_sec", "count")))
    g = g.sort_values("depth").reset_index(drop=True)
    return g

def main():
    fig, axes = plt.subplots(len(BOARDS), 2, figsize=(10.5, 7.2), sharex="col")
    if len(BOARDS) == 1:
        axes = np.array([axes])  # normalize shape

    for r, (code, label) in enumerate(BOARDS):
        df = load_board(code)
        ax_t, ax_e = axes[r, 0], axes[r, 1]

        if df is None or df.empty:
            for ax in (ax_t, ax_e):
                ax.text(0.5, 0.5, f"No BFS/DFS data for {label}", ha="center", va="center")
                ax.axis("off")
            continue

        gb = agg_curves(df, "BFS")
        gd = agg_curves(df, "DFS")

        # ---- time (seconds)
        if not gb.empty:
            ax_t.errorbar(gb["depth"], gb["time_mean"], yerr=gb["time_sem"],
                          label="BFS", color=C_BFS, marker="o", lw=2, capsize=3)
        if not gd.empty:
            ax_t.errorbar(gd["depth"], gd["time_mean"], yerr=gd["time_sem"],
                          label="DFS", color=C_DFS, marker="^", lw=2, capsize=3, ls="--")
        ax_t.set_title(label)
        ax_t.set_ylabel("Time (s)")
        ax_t.grid(True, alpha=0.25, ls=":")

        # ---- expanded
        if not gb.empty:
            ax_e.errorbar(gb["depth"], gb["exp_mean"], yerr=gb["exp_sem"],
                          label="BFS", color=C_BFS, marker="o", lw=2, capsize=3)
        if not gd.empty:
            ax_e.errorbar(gd["depth"], gd["exp_mean"], yerr=gd["exp_sem"],
                          label="DFS", color=C_DFS, marker="^", lw=2, capsize=3, ls="--")
        ax_e.set_title(label)
        ax_e.set_ylabel("Expanded nodes")
        ax_e.grid(True, alpha=0.25, ls=":")

        # common x tick marks (even depths)
        for ax in (ax_t, ax_e):
            ax.set_xlabel("Depth")
            ax.set_xticks(range(4, 22, 2))
        
        # # (add inside your plotting code, after you draw each subplot)
        # BFS_CAP = 14
        # ax.axvspan(BFS_CAP + 0.5, 20.5, color="gray", alpha=0.08)
        # ax.text(BFS_CAP + 0.6, ax.get_ylim()[1]*0.9, "BFS not run\n(memory cap)", fontsize=8, color="gray")
        # --- add the BFS "not run" shading to BOTH subplots in the row ---
        BFS_CAP = 14
        for ax in (ax_t, ax_e):
            ax.axvspan(BFS_CAP + 0.5, 20.5, color="gray", alpha=0.08, zorder=0)
            y0, y1 = ax.get_ylim()
            ax.text(
                BFS_CAP + 0.6,
                y1 - 0.06*(y1 - y0),     # 6% down from top so it never collides
                "BFS not run\n(memory cap)",
                fontsize=8,
                color="gray",
                ha="left",
                va="top",
            )


    # one shared legend across subplots
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("BFS vs DFS — per-depth runtime and expansions", y=0.995, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = OUT / "bfs_dfs_grid.png"
    fig.savefig(out, dpi=200)
    print("✅", out)

if __name__ == "__main__":
    main()
