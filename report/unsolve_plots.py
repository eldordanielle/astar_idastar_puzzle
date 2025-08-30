#!/usr/bin/env python3
import os, re, glob
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_FIGS = Path("report/figs"); OUT_FIGS.mkdir(parents=True, exist_ok=True)
OUT_TABS = Path("report/tables"); OUT_TABS.mkdir(parents=True, exist_ok=True)

BOARDS = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]
EXCLUDE = re.compile(r"(bpmx|bfs|dfs|unsolv|unsolvable|smoke|sanity|astar_vs_ida)", re.I)

# Okabe–Ito palette (color-blind friendly)
C_SOLV = "#0072B2"  # blue solid
C_UNSV = "#E69F00"  # orange dashed

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def load_solvable_ida(board: str) -> pd.DataFrame | None:
    """Collect IDA* Manhattan runs for SOLVABLE cases across files, termination=ok or not (we track timeouts)."""
    pats = [
        f"results/{board}_manhattan.csv",
        f"results/{board}_manhattan_*.csv",
        f"results/{board}_*_{'manhattan'}.csv",
    ]
    dfs=[]
    for pat in pats:
        for p in glob.glob(pat):
            name = os.path.basename(p)
            if EXCLUDE.search(name): 
                continue
            try:
                df = pd.read_csv(p)
            except Exception:
                continue
            need = {"algorithm","heuristic","depth","time_sec","termination","solvable"}
            if not need.issubset(df.columns): 
                continue
            part = df[(df["algorithm"]=="IDA*") & (df["solvable"]==1)].copy()
            if not part.empty:
                dfs.append(part)
    if not dfs:
        return None
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    df["kind"]="solv"
    return df

def load_unsolvable_ida(board: str) -> pd.DataFrame | None:
    """Load the merged unsolvable file created by the array; filter to IDA* and solvable=0."""
    p = f"results/{board}_unsolv_ida.csv"
    if not os.path.exists(p):
        return None
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    need = {"algorithm","depth","time_sec","termination","solvable"}
    if not need.issubset(df.columns): 
        return None
    df = df[(df["algorithm"]=="IDA*") & (df["solvable"]==0)].copy()
    df["kind"]="unsolv"
    return df

def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per (kind, depth): means, SEM, n, and timeout rate."""
    # n_total per (kind,depth)
    n_total = df.groupby(["kind","depth"]).size().rename("n_total").reset_index()
    # finished rows (termination=ok)
    ok = df[df["termination"].fillna("ok")=="ok"].copy()
    g = (ok.groupby(["kind","depth"], as_index=False)
            .agg(time_mean=("time_sec","mean"),
                 time_sem =("time_sec", sem),
                 exp_mean =("expanded","mean"),
                 exp_sem  =("expanded", sem),
                 n=("time_sec","count")))
    out = pd.merge(g, n_total, on=["kind","depth"], how="right").fillna({"n":0})
    out["timeout_rate"] = (1 - (out["n"]/out["n_total"]).clip(lower=0)) * 100.0
    return out.sort_values(["kind","depth"]).reset_index(drop=True)

def plot_grid(solvs, unsolvs):
    fig, axes = plt.subplots(len(BOARDS), 2, figsize=(11.2, 9.5), sharex="col")
    for r,(code,label) in enumerate(BOARDS):
        a = solvs.get(code); b = unsolvs.get(code)
        ax_t, ax_e = axes[r,0], axes[r,1]

        def draw(ax, part, color, ls, m):
            if part is None or part.empty: return
            ax.errorbar(part["depth"], part["time_mean"], yerr=part["time_sem"],
                        color=color, ls=ls, marker=m, lw=2.2, ms=5.5, capsize=3, label=None)

        def draw_e(ax, part, color, ls, m):
            if part is None or part.empty: return
            ax.errorbar(part["depth"], part["exp_mean"], yerr=part["exp_sem"],
                        color=color, ls=ls, marker=m, lw=2.2, ms=5.5, capsize=3, label=None)

        # time
        if a is not None: draw(ax_t, a, C_SOLV, "-", "o")
        if b is not None: draw(ax_t, b, C_UNSV, "--", "^")
        ax_t.set_title(label); ax_t.set_ylabel("Time (s)"); ax_t.grid(True, alpha=0.25, ls=":")
        ax_t.set_xticks(range(4,22,2))

        # expansions
        if a is not None: draw_e(ax_e, a, C_SOLV, "-", "o")
        if b is not None: draw_e(ax_e, b, C_UNSV, "--", "^")
        ax_e.set_title(label); ax_e.set_ylabel("Expanded"); ax_e.grid(True, alpha=0.25, ls=":")
        ax_e.set_xticks(range(4,22,2))

        # annotate timeout % above each point (if any)
        for ax, part in ((ax_t, a), (ax_t, b), (ax_e, a), (ax_e, b)):
            if part is None or part.empty: continue
            for d, rate, ym in zip(part["depth"], part["timeout_rate"], 
                                   part["time_mean"] if ax is ax_t else part["exp_mean"]):
                if np.isfinite(ym) and rate>0:
                    ax.text(d, ym*1.05, f"{rate:.0f}%", fontsize=7, ha="center", color="gray")

    # shared legend + title
    # Create manual legend
    l1 = matplotlib.lines.Line2D([0],[0], color=C_SOLV, marker="o", lw=2.2, ls="-", label="Solvable")
    l2 = matplotlib.lines.Line2D([0],[0], color=C_UNSV, marker="^", lw=2.2, ls="--", label="Unsolvable")
    fig.legend([l1,l2], ["Solvable","Unsolvable"], ncol=2, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("Solvable vs. Unsolvable (IDA*, Manhattan): runtime and expansions", y=0.995, fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.955])
    out = OUT_FIGS / "unsolv_vs_solv_grid.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print("✅", out)

def ratio_sem(mean_u, sem_u, mean_s, sem_s):
    r = mean_u/mean_s
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.sqrt((sem_u/mean_u)**2 + (sem_s/mean_s)**2)
    return r, r*rel

def plot_ratio_grid(solvs, unsolvs):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.5), sharey=True)
    axes = axes.ravel()
    for ax, (code,label) in zip(axes, BOARDS):
        a = solvs.get(code); b = unsolvs.get(code)
        if a is None or a.empty or b is None or b.empty:
            ax.text(0.5,0.5,"missing data",ha="center"); ax.axis("off"); continue
        # align on common depths where both groups have means
        common = sorted(set(a["depth"]).intersection(b["depth"]))
        a2 = a.set_index("depth").loc[common]
        b2 = b.set_index("depth").loc[common]
        r, s = ratio_sem(b2["time_mean"].values, b2["time_sem"].values,
                         a2["time_mean"].values, a2["time_sem"].values)
        ax.errorbar(common, r, yerr=s, color="#009E73", marker="o", lw=2.2, capsize=3)
        ax.axhline(1.0, ls=":", c="gray")
        ax.set_ylim(0.8, 5.0)
        ax.set_title(label); ax.set_xlabel("Depth"); ax.set_ylabel("Unsolvable / Solvable (time)")
        ax.grid(True, alpha=0.25, ls=":")
        ax.set_xticks(range(4,22,2))
    fig.suptitle("Penalty of Unsolvable vs. Solvable (IDA*, Manhattan): time ratio", y=0.98)
    fig.tight_layout(rect=[0,0,1,0.96])
    out = OUT_FIGS / "unsolv_penalty_grid.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print("✅", out)

def write_appendix_table(solvs, unsolvs):
    rows=[]
    for code,label in BOARDS:
        for name,part in (("Solvable", solvs.get(code)), ("Unsolvable", unsolvs.get(code))):
            if part is None or part.empty: 
                continue
            tmp = part.copy()
            tmp.insert(0, "Board", label)
            tmp.insert(1, "Class", name)
            rows.append(tmp)
    if not rows:
        print("no data for appendix table"); return
    tab = pd.concat(rows, ignore_index=True)
    # Clean display
    disp = tab.rename(columns={
        "depth":"Depth","time_mean":"Time (s, mean)","time_sem":"Time (s, SEM)",
        "exp_mean":"Expanded (mean)","exp_sem":"Expanded (SEM)",
        "n":"n_ok","n_total":"n_total","timeout_rate":"Timeout (%)"
    }).copy()
    disp["Time (s, mean)"] = disp["Time (s, mean)"].map(lambda v: float(v) if pd.notna(v) else np.nan)
    disp["Time (s, SEM)"]  = disp["Time (s, SEM)"].map(lambda v: float(v) if pd.notna(v) else np.nan)
    # Write Excel
    xls = OUT_TABS / "unsolv_summary.xlsx"
    with pd.ExcelWriter(xls, engine="xlsxwriter") as xw:
        disp.to_excel(xw, sheet_name="summary", index=False)
    print("✅", xls)

def main():
    solvs, unsolvs = {}, {}
    for code,_ in BOARDS:
        a = load_solvable_ida(code)
        b = load_unsolvable_ida(code)
        solvs[code]   = summarize(a) if a is not None else None
        unsolvs[code] = summarize(b) if b is not None else None

    plot_grid(solvs, unsolvs)
    plot_ratio_grid(solvs, unsolvs)
    write_appendix_table(solvs, unsolvs)

if __name__ == "__main__":
    main()
