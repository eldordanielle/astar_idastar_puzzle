#!/usr/bin/env python3
import os, glob
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------- I/O ----------
OUT_FIGS = Path("report/figs"); OUT_FIGS.mkdir(parents=True, exist_ok=True)
OUT_TABS = Path("report/tables"); OUT_TABS.mkdir(parents=True, exist_ok=True)

BOARDS = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]
HEUR_ALIASES = {"manhattan":["manhattan"],
                "linear":["linear","linear_conflict"]}

EXCLUDE_TAGS = ("bpmx","unsolv","unsolvable","bfs","dfs","astar_vs_ida","smoke","sanity")

# Colors/styles (match rest of report)
C_MAN = "#0072B2"    # Manhattan
C_LC  = "#E69F00"    # Linear Conflict
STYLE_ASTAR = dict(marker="o", lw=2.2, capsize=3, ls="-")
STYLE_IDA   = dict(marker="^", lw=2.2, capsize=3, ls="--")

# ---------- helpers ----------
def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1)/np.sqrt(n)

def _find_files(board: str, heur_key: str) -> list[Path]:
    pats = []
    for alias in HEUR_ALIASES[heur_key]:
        pats += [
            f"results/{board}_{alias}.csv",
            f"results/{board}_{alias}_*.csv",
            f"results/{board}_*_{alias}.csv",
            f"results/{board}_*_{alias}_*.csv",
        ]
    out = []
    for pat in pats:
        for p in glob.glob(pat):
            name = os.path.basename(p).lower()
            if any(tag in name for tag in EXCLUDE_TAGS):  # filter BPMX, unsolv, baselines, etc.
                continue
            out.append(Path(p))
    # unique, stable
    seen, uniq = set(), []
    for p in sorted(out):
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def _load_ok(p: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    need = {"algorithm","depth","time_sec"}
    if not need.issubset(df.columns):
        return None
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok")=="ok"]
    # keep only A*/IDA*
    df = df[df["algorithm"].isin(["A*","IDA*"])].copy()
    # add missing numeric cols as NaN
    for c in ("expanded","generated","duplicates","peak_open","peak_closed",
              "peak_recursion","bound_final"):
        if c not in df.columns:
            df[c] = np.nan
    return df

def load_board_heur(board: str, heur_key: str) -> pd.DataFrame | None:
    files = _find_files(board, heur_key)
    dfs = []
    for p in files:
        d = _load_ok(p)
        if d is not None and not d.empty:
            d["heuristic"] = "Man" if heur_key=="manhattan" else "LC"
            d["board"] = dict(BOARDS)[board]
            dfs.append(d)
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True).drop_duplicates()

def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """Per (board, heur, algo, depth) means & SEMs, plus derived rates."""
    g = (df.groupby(["board","heuristic","algorithm","depth"], as_index=False)
           .agg(expanded_mean=("expanded","mean"), expanded_sem=("expanded", sem),
                generated_mean=("generated","mean"), generated_sem=("generated", sem),
                duplicates_mean=("duplicates","mean"), duplicates_sem=("duplicates", sem),
                time_mean=("time_sec","mean"), time_sem=("time_sec", sem),
                peak_open_mean=("peak_open","mean"), peak_open_sem=("peak_open", sem),
                peak_closed_mean=("peak_closed","mean"), peak_closed_sem=("peak_closed", sem),
                peak_rec_mean=("peak_recursion","mean"), peak_rec_sem=("peak_recursion", sem),
                n=("time_sec","count")))
    # duplicate rate = duplicates / expanded (guard zeros/NaNs)
    g["dup_rate"] = g["duplicates_mean"] / g["expanded_mean"].replace(0, np.nan)
    return g

# ---------- Figure X: duplicate rate ----------
def plot_dup_rate_grid(summary: pd.DataFrame):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, (code, label) in zip(axes, BOARDS):
        part = summary[summary["board"] == label]
        if part.empty:
            ax.text(0.5, 0.5, f"No data for {label}", ha="center", va="center")
            ax.axis("off"); continue

        for heur, color in [("Man", C_MAN), ("LC", C_LC)]:
            a = part[(part["heuristic"]==heur) & (part["algorithm"]=="A*")].sort_values("depth")
            i = part[(part["heuristic"]==heur) & (part["algorithm"]=="IDA*")].sort_values("depth")
            if not a.empty:
                ax.errorbar(a["depth"], a["dup_rate"], yerr=None, color=color, label=f"A* {heur}",
                            **STYLE_ASTAR)
            if not i.empty:
                ax.errorbar(i["depth"], i["dup_rate"], yerr=None, color=color, label=f"IDA* {heur}",
                            **STYLE_IDA)
        ax.set_title(label)
        ax.set_xlabel("Depth"); ax.set_ylabel("duplicates / expanded")
        ax.grid(True, alpha=0.25, ls=":")
        ax.set_ylim(bottom=0)  # rates cannot be negative
        ax.set_xticks(range(4, 22, 2))

    # one shared legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("Duplicate rate vs depth — A* (solid) vs IDA* (dashed); Man (blue) vs LC (gold)", y=0.995)
    fig.tight_layout(rect=[0,0,1,0.95])
    out = OUT_FIGS / "dup_rate_grid.png"
    fig.savefig(out, dpi=200)
    print("✅ wrote", out)

# ---------- Figure Y: memory proxies ----------
def plot_memory_grid(summary: pd.DataFrame):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), sharex=True)
    axes = axes.ravel()
    for ax, (code, label) in zip(axes, BOARDS):
        part = summary[summary["board"] == label]
        if part.empty:
            ax.text(0.5, 0.5, f"No data for {label}", ha="center", va="center")
            ax.axis("off"); continue

        # A*: peak_open + peak_closed; IDA*: peak_recursion (plotted on same axis for quick contrast)
        for heur, color in [("Man", C_MAN), ("LC", C_LC)]:
            a = part[(part["heuristic"]==heur) & (part["algorithm"]=="A*")].copy()
            i = part[(part["heuristic"]==heur) & (part["algorithm"]=="IDA*")].copy()
            a = a.sort_values("depth"); i = i.sort_values("depth")
            if not a.empty:
                a_mem = (a["peak_open_mean"].fillna(0) + a["peak_closed_mean"].fillna(0)).values
                ax.errorbar(a["depth"].values, a_mem, color=color, label=f"A* mem {heur}", **STYLE_ASTAR)
            if not i.empty:
                ax.errorbar(i["depth"].values, i["peak_rec_mean"].values,
                            color=color, label=f"IDA* mem {heur}", **STYLE_IDA)

        ax.set_title(label)
        ax.set_xlabel("Depth"); ax.set_ylabel("memory proxy (A*: OPEN+CLOSED; IDA*: recursion)")
        ax.grid(True, alpha=0.25, ls=":")
        ax.set_xticks(range(4, 22, 2))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("Memory proxies vs depth — A* (solid) = OPEN+CLOSED; IDA* (dashed) = recursion depth", y=0.995)
    fig.tight_layout(rect=[0,0,1,0.95])
    out = OUT_FIGS / "memory_proxy_grid.png"
    fig.savefig(out, dpi=200)
    print("✅ wrote", out)

# ---------- Appendix table ----------
def write_appendix_table(summary: pd.DataFrame):
    # build compact table
    tbl = summary.copy()
    tbl["A*_mem_sum"] = (tbl["peak_open_mean"].fillna(0) + tbl["peak_closed_mean"].fillna(0))
    keep = ["board","heuristic","algorithm","depth",
            "expanded_mean","generated_mean","duplicates_mean","dup_rate",
            "A*_mem_sum","peak_rec_mean","time_mean","time_sem","n"]
    tbl = tbl[keep].rename(columns={
        "board":"Board","heuristic":"Heur","algorithm":"Alg.","depth":"d",
        "expanded_mean":"Exp (mean)","generated_mean":"Gen (mean)",
        "duplicates_mean":"Dup (mean)","dup_rate":"Dup/Exp",
        "A*_mem_sum":"A* mem (OPEN+CLOSED)","peak_rec_mean":"IDA* mem (rec.depth)",
        "time_mean":"Time (s, mean)","time_sem":"Time (s, SEM)","n":"n"
    })

    # nice rounding/formatting
    tbl["Dup/Exp"] = tbl["Dup/Exp"].astype(float).round(3)
    tbl["Time (s, mean)"] = tbl["Time (s, mean)"].astype(float).map(lambda v: f"{v:.6f}")
    tbl["Time (s, SEM)"]  = tbl["Time (s, SEM)"].astype(float).map(lambda v: f"{v:.6f}")

    out = OUT_TABS / "dup_mem_summary.xlsx"
    with pd.ExcelWriter(out, engine="xlsxwriter") as xw:
        # NOTE: groupby on a single column name (not ["Board"]) -> scalar key
        for brd, part in tbl.groupby("Board", sort=False):
            safe = str(brd).replace("×", "x")
            # Excel sheet-name safety
            for bad in ':\\/*?[]':
                safe = safe.replace(bad, '-')
            safe = safe[:31] or "Sheet"
            part = part.sort_values(["Heur","Alg.","d"])
            part.to_excel(xw, sheet_name=safe, index=False)
    print("✅ wrote", out)

# ---------- main ----------
def main():
    all_blocks = []
    for code, _ in BOARDS:
        for hk in ("manhattan","linear"):
            df = load_board_heur(code, hk)
            if df is not None and not df.empty:
                all_blocks.append(df)
    if not all_blocks:
        raise SystemExit("No A*/IDA* CSVs found under results/.")
    df = pd.concat(all_blocks, ignore_index=True)
    summary = aggregate(df)

    plot_dup_rate_grid(summary)
    plot_memory_grid(summary)
    write_appendix_table(summary)

if __name__ == "__main__":
    main()
