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

BOARDS = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]
ALGORITHMS = [("A*", "#0072B2", "-"), ("IDA*", "#E69F00", "--")]  # (name, color, linestyle)
EXCLUDE = ("bpmx", "bfs", "dfs", "unsolv_check", "sanity", "smoke")

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def find_csvs(board: str) -> list[Path]:
    pats = [
        f"results/{board}_*.csv",
        f"results/**/*{board}*.csv",
    ]
    out = []
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            name = os.path.basename(p).lower()
            if any(tag in name for tag in EXCLUDE):
                continue
            out.append(Path(p))
    # stable & unique
    seen, uniq = set(), []
    for p in sorted(out):
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def load_board(board: str) -> pd.DataFrame | None:
    files = find_csvs(board)
    if not files: return None
    frames = []
    for p in files:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        need = {"algorithm","heuristic","depth","time_sec","solvable"}
        if not need.issubset(df.columns):
            continue
        # keep A* / IDA* only, any heuristic (we’ll label Manhattan in caption, but LC works too)
        df = df[df["algorithm"].isin(["A*","IDA*"])].copy()
        # drop timeouts (exhausted is allowed for unsolvable)
        if "termination" in df.columns:
            df = df[df["termination"].fillna("ok") != "timeout"]
        if df.empty:
            continue
        # best-effort: ensure numeric depth, solvable∈{0,1}
        df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
        df["solvable"] = pd.to_numeric(df["solvable"], errors="coerce")
        df = df.dropna(subset=["depth","solvable"])
        frames.append(df)
    if not frames: return None
    return pd.concat(frames, ignore_index=True).drop_duplicates()

def ratios_by_depth(df: pd.DataFrame, algo: str, metric: str):
    """
    Compute unsolvable/solvable ratio with SEM propagation for a given metric
    (metric in {"generated","time_sec"}).
    """
    sub = df[df["algorithm"] == algo]
    if sub.empty: return None

    # group means/sem by (solvable, depth)
    g = (sub.groupby(["solvable","depth"], as_index=False)
             .agg(mu=(metric,"mean"), se=(metric, sem), n=("time_sec","count")))

    solv = g[g["solvable"] == 1].set_index("depth")
    uns  = g[g["solvable"] == 0].set_index("depth")
    common = sorted(set(solv.index).intersection(uns.index))
    if not common:
        return None

    mu_s, se_s = solv.loc[common,"mu"].values, solv.loc[common,"se"].values
    mu_u, se_u = uns.loc[common,"mu"].values,  uns.loc[common,"se"].values

    # ratio and SEM propagation (independent samples)
    r = mu_u / mu_s
    with np.errstate(divide="ignore", invalid="ignore"):
        rsem = np.sqrt((se_u/np.maximum(mu_u,1e-12))**2 + (se_s/np.maximum(mu_s,1e-12))**2) * r
    return np.array(common), r, rsem

def main():
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.2), sharex=True, sharey="row")
    # Top row: generated ratio; Bottom row: time ratio
    for j,(code,label) in enumerate(BOARDS):
        df = load_board(code)

        # Generated ratio panel
        axg = axes[0, j]
        if df is None or df.empty or df["solvable"].min() == 1:
            axg.text(0.5, 0.5, "No unsolvable data", ha="center", va="center")
            axg.axis("off")
        else:
            for name, color, ls in ALGORITHMS:
                cur = ratios_by_depth(df, name, "generated")
                if cur is None: continue
                x,y,s = cur
                axg.errorbar(x, y, yerr=s, label=name, color=color, ls=ls, marker="o", lw=2, capsize=3)
            axg.axhline(1.0, ls=":", c="gray")
            axg.set_title(label)
            if j == 0: axg.set_ylabel("Unsolv / Solv (generated)")
            axg.set_xticks(range(4, 22, 2))
            axg.grid(True, alpha=0.25, ls=":")

        # Time ratio panel
        axt = axes[1, j]
        if df is None or df.empty or df["solvable"].min() == 1:
            axt.axis("off")
        else:
            for name, color, ls in ALGORITHMS:
                cur = ratios_by_depth(df, name, "time_sec")
                if cur is None: continue
                x,y,s = cur
                axt.errorbar(x, y, yerr=s, label=name, color=color, ls=ls, marker="o", lw=2, capsize=3)
            axt.axhline(1.0, ls=":", c="gray")
            if j == 0: axt.set_ylabel("Unsolv / Solv (time)")
            axt.set_xlabel("Depth")
            axt.set_xticks(range(4, 22, 2))
            axt.grid(True, alpha=0.25, ls=":")

    # Shared legend
    handles, labels = [], []
    for name, color, ls in ALGORITHMS:
        h, = plt.plot([], [], color=color, ls=ls, marker="o", label=name)
        handles.append(h); labels.append(name)
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.98))

    fig.suptitle("Unsolvable vs. solvable — per-depth ratios across boards (↑ >1 means harder unsolvable)", y=0.995, fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out = OUT / "unsolvable_ratio_grid.png"
    fig.savefig(out, dpi=200)
    print("✅", out)

if __name__ == "__main__":
    main()
