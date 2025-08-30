#!/usr/bin/env python3
"""
Regenerates 'solvable vs unsolvable' grids + ratio plots for IDA* runs (Manhattan).
Adds: dynamic ratio Y-limits, larger titles, numeric coercion, de-dup,
optional n and timeout annotations, robust unsolvable labeling.
"""

from __future__ import annotations
import os, re, glob
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------- configuration -----------------------

OUT_FIGS   = Path("report/figs");   OUT_FIGS.mkdir(parents=True, exist_ok=True)
OUT_TABLES = Path("report/tables"); OUT_TABLES.mkdir(parents=True, exist_ok=True)

BOARDS: list[Tuple[str,str]] = [
    ("p8",   "P 8"),
    ("p15",  "P 15"),
    ("r3x4", "R 3×4"),
    ("r3x5", "R 3×5"),
]

DEPTHS    = list(range(4, 21, 2))
OK_TERMS  = {"ok", "exhausted"}      # considered completed
ONLY_MANHATTAN = True                # keep only Manhattan when detectable

# Style
BOARD_TITLE_FZ = 13
SUPTITLE_FZ    = 16
ANNOTATE_N           = True
ANNOTATE_TIMEOUTS    = True
TIMEOUT_MARK_COLOR   = "#D55E00"     # red/orange '×' at top if timeouts

# Colors (Okabe–Ito)
C_SOLV  = "#0072B2"   # blue
C_UNSV  = "#E69F00"   # orange
C_RATIO = "#CC79A7"   # purple

FILE_EXCLUDE = re.compile(r"(bfs|dfs|astar_vs_ida|smoke|sanity)", re.I)

# ----------------------- helpers -----------------------

def sem(x) -> float:
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def _bool_from_any(v):
    if pd.isna(v): return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        try: return bool(int(v))
        except Exception: return np.nan
    s = str(v).strip().lower()
    if s in {"1","true","t","yes","y","1.0"}:  return True
    if s in {"0","false","f","no","n","0.0"}:  return False
    return np.nan

def _map_solvable(series: pd.Series) -> pd.Series:
    return series.map(_bool_from_any)

def _maybe_filter_manhattan(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    if not ONLY_MANHATTAN:
        return df
    if "heuristic" in df.columns:
        mask = df["heuristic"].astype(str).str.lower().str.contains("manhattan")
        return df[mask]
    # No heuristic column → rely on filename hints
    name = filename.lower()
    if "linear" in name or "conflict" in name:
        return pd.DataFrame(columns=df.columns)
    return df

def _guess_unsolv_from_filename(name: str) -> bool | None:
    n = name.lower()
    if "unsolv" in n or "unsolvable" in n: return True
    if "solv" in n and "unsolv" not in n:  return False
    return None

def load_board(board_code: str) -> pd.DataFrame:
    """Load all IDA* rows for one board with robust labeling and filtering."""
    patterns = [
        f"results/{board_code}_*.csv",
        f"results/**/*{board_code}*.csv",
        f"results/{board_code}*.csv",
    ]
    files = []
    for pat in patterns:
        files += [Path(p) for p in glob.glob(pat, recursive=True)]
    files = sorted(set(p for p in files if not FILE_EXCLUDE.search(p.name)))

    if not files:
        print(f"!! {board_code}: no files matched")
        return pd.DataFrame()

    rows = []
    print(f"\n== Loading {board_code}: {len(files)} files ==")
    for p in files:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue

        # strip unnamed cols, coerce numerics
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        for c in ("depth","time_sec","expanded"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["depth","time_sec"])
        df["depth"] = df["depth"].astype(int)

        need_any = {"algorithm","depth","time_sec"}
        if not need_any.issubset(df.columns):
            continue

        # Keep IDA* (BPMX variants allowed)
        ida_mask = df["algorithm"].astype(str).str.contains(r"IDA\*", regex=True)
        if not ida_mask.any():
            continue
        df = df[ida_mask].copy()

        # Heuristic filter (Manhattan when detectable)
        df = _maybe_filter_manhattan(df, p.name)
        if df.empty:
            continue

        # Restrict to our depths
        df = df[df["depth"].isin(DEPTHS)].copy()
        if df.empty:
            continue

        # Expanded column (optional)
        if "expanded" not in df.columns:
            df["expanded"] = np.nan

        # Termination (keep original; we'll aggregate by OK_TERMS later)
        if "termination" not in df.columns:
            df["termination"] = "ok"
        df["termination"] = df["termination"].astype(str).str.lower().str.strip()

        # Solvable flag — map column if present
        if "solvable" in df.columns:
            df["solvable"] = _map_solvable(df["solvable"])
        else:
            df["solvable"] = np.nan

        # Override mislabeled files using filename
        file_says_unsolv = _guess_unsolv_from_filename(p.name)
        if file_says_unsolv is True:
            df["solvable"] = False
        elif file_says_unsolv is False:
            df["solvable"] = True

        # If still unknown (NaN), drop to avoid mixing
        df = df[df["solvable"].isin([True, False])]

        if df.empty:
            continue

        # De-duplicate rows (common when merging many CSVs)
        df = df.drop_duplicates()

        rows.append(df)

        # quick counts
        s_cnt = int((df["solvable"] == True ).sum())
        u_cnt = int((df["solvable"] == False).sum())
        if s_cnt or u_cnt:
            print(f"{p.name:>40s}  S={s_cnt:4d}  U={u_cnt:4d}")

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)

def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per (solvable,depth): mean/SEM for time & expansions, n_total, timeout%."""
    if df.empty:
        return pd.DataFrame(columns=[
            "solvable","depth","n_total","n","time_mean","time_sem","exp_mean","exp_sem","timeout_rate"
        ])

    total = df.groupby(["solvable","depth"], as_index=False).size().rename(columns={"size":"n_total"})

    fin = df[df["termination"].isin(OK_TERMS)].copy()
    agg = (fin.groupby(["solvable","depth"], as_index=False)
              .agg(time_mean=("time_sec","mean"),
                   time_sem =("time_sec", sem),
                   exp_mean =("expanded","mean"),
                   exp_sem  =("expanded", sem),
                   n        =("time_sec","count")))

    out = pd.merge(total, agg, on=["solvable","depth"], how="left")
    out["n"] = out["n"].fillna(0).astype(int)
    out["timeout_rate"] = (1 - (out["n"] / out["n_total"]).clip(0,1)) * 100.0
    return out.sort_values(["solvable","depth"]).reset_index(drop=True)

def print_depth_counts(df: pd.DataFrame, label: str):
    if df.empty:
        print(f"!! {label}: no rows after filtering")
        return
    print(f"-- {label}: depth counts (solvable/unsolvable)")
    s = df[df["solvable"]==True ].groupby("depth").size()
    u = df[df["solvable"]==False].groupby("depth").size()
    for d in DEPTHS:
        cs = int(s.get(d,0)); cu = int(u.get(d,0))
        if cs or cu:
            print(f"   d={d:2d}: S={cs:4d}  U={cu:4d}")

# ----------------------- plotting -----------------------

def plot_runtime_and_expanded(per_board: Dict[str,pd.DataFrame]):
    fig, axes = plt.subplots(len(BOARDS), 2, figsize=(12, 10), sharex="col")
    axes = np.array(axes).reshape(len(BOARDS), 2)

    for r, (code, label) in enumerate(BOARDS):
        df = per_board.get(code, pd.DataFrame())
        print_depth_counts(df, label)

        axT, axE = axes[r]

        if df.empty:
            for ax in (axT, axE):
                ax.text(0.5,0.5,"No data", ha="center", va="center"); ax.axis("off")
            continue

        summ = summarize(df)
        sT = summ[summ["solvable"]==True ]
        uT = summ[summ["solvable"]==False]

        # Time
        if not sT.empty:
            axT.errorbar(sT["depth"], sT["time_mean"], yerr=sT["time_sem"],
                         label="Solvable", color=C_SOLV, marker="o", lw=2, capsize=3)
        if not uT.empty:
            axT.errorbar(uT["depth"], uT["time_mean"], yerr=uT["time_sem"],
                         label="Unsolvable", color=C_UNSV, marker="^", lw=2, capsize=3, ls="--")
        axT.set_title(label, fontsize=BOARD_TITLE_FZ); axT.set_ylabel("Time (s)")
        axT.grid(alpha=0.25, ls=":")

        # Expansions
        if not sT.empty:
            axE.errorbar(sT["depth"], sT["exp_mean"], yerr=sT["exp_sem"],
                         label="Solvable", color=C_SOLV, marker="o", lw=2, capsize=3)
        if not uT.empty:
            axE.errorbar(uT["depth"], uT["exp_mean"], yerr=uT["exp_sem"],
                         label="Unsolvable", color=C_UNSV, marker="^", lw=2, capsize=3, ls="--")
        axE.set_title(label, fontsize=BOARD_TITLE_FZ); axE.set_ylabel("Expanded")
        axE.grid(alpha=0.25, ls=":")

        for ax in (axT, axE):
            ax.set_xlabel("Depth"); ax.set_xticks(DEPTHS)

        # Optional annotations
        if ANNOTATE_N:
            axT.text(0.98, 0.02, f"n={int(summ['n'].sum())}", transform=axT.transAxes,
                     ha="right", va="bottom", fontsize=8, color="gray")
        if ANNOTATE_TIMEOUTS:
            # put an × at the top of the time subplot for any depth with timeouts
            top = axT.get_ylim()[1]
            for part in (sT, uT):
                for d, rate in zip(part["depth"], part["timeout_rate"]):
                    if rate > 0:
                        axT.text(d, top*0.98, "×", ha="center", va="top",
                                 fontsize=9, color=TIMEOUT_MARK_COLOR)

    # Shared legend
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=2, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 0.98))
    title_suffix = "IDA*, Manhattan" if ONLY_MANHATTAN else "IDA*"
    fig.suptitle(f"Solvable vs. Unsolvable ({title_suffix}): runtime and expansions",
                 y=0.995, fontsize=SUPTITLE_FZ)
    fig.tight_layout(rect=[0,0,1,0.95])

    out = OUT_FIGS / "unsolv_vs_solv_grid.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("✅", out)

def plot_ratio_penalty(per_board: Dict[str,pd.DataFrame]):
    # First pass: compute all ratios to choose a good shared y-limit
    all_ratios = []
    precomp = {}
    for code, _ in BOARDS:
        df = per_board.get(code, pd.DataFrame())
        summ = summarize(df) if not df.empty else pd.DataFrame()
        s = summ[summ["solvable"]==True ].set_index("depth")
        u = summ[summ["solvable"]==False].set_index("depth")
        common = sorted(set(s.index).intersection(u.index))
        if common:
            r  = (u.loc[common,"time_mean"] / s.loc[common,"time_mean"]).to_numpy()
            rs = np.sqrt((u.loc[common,"time_sem"]/u.loc[common,"time_mean"])**2 +
                         (s.loc[common,"time_sem"]/s.loc[common,"time_mean"])**2).to_numpy() * r
            precomp[code] = (common, r, rs)
            all_ratios.extend(r.tolist())

    # Choose dynamic y-limit so lines sit mid-axis, but keep reasonable bounds
    if all_ratios:
        rmax = float(np.nanmax(all_ratios))
        # y_low  = 0.85
        y_low = 0
        y_high = max(1.6, min(4.0, rmax * 1.35))

    else:
        y_low, y_high = 0.8, 5.0

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, (code, label) in zip(axes, BOARDS):
        if code not in precomp:
            ax.text(0.5,0.5,"No data", ha="center", va="center"); ax.axis("off"); continue
        common, r, rs = precomp[code]
        ax.errorbar(common, r, yerr=rs, marker="o", lw=2, capsize=3, color=C_RATIO)
        ax.axhline(1.0, ls=":", c="gray")
        ax.set_title(label, fontsize=BOARD_TITLE_FZ); ax.grid(alpha=0.25, ls=":")
        ax.set_xlabel("Depth"); ax.set_ylabel("Unsolvable / Solvable (time)")
        ax.set_xticks(DEPTHS)
        ax.set_ylim(y_low, y_high)

    title_suffix = "IDA*, Manhattan" if ONLY_MANHATTAN else "IDA*"
    fig.suptitle(f"Penalty of Unsolvable vs. Solvable ({title_suffix}): time ratio",
                 y=0.99, fontsize=SUPTITLE_FZ)
    fig.tight_layout(rect=[0,0,1,0.96])
    out = OUT_FIGS / "unsolv_penalty_ratio.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("✅", out)

def write_appendix_table(per_board: Dict[str,pd.DataFrame]):
    rows = []
    for code, label in BOARDS:
        df = per_board.get(code, pd.DataFrame())
        if df.empty: continue
        summ = summarize(df)
        for solv_flag, name in ((True, "Solvable"), (False, "Unsolvable")):
            part = summ[summ["solvable"]==solv_flag].copy()
            if part.empty: continue
            part.insert(0, "Board", label)
            part.insert(1, "Class", name)
            rows.append(part)
    if not rows:
        print("no data for appendix table"); return

    tab = pd.concat(rows, ignore_index=True).rename(columns={
        "depth":"Depth","time_mean":"Time (s, mean)","time_sem":"Time (s, SEM)",
        "exp_mean":"Expanded (mean)","exp_sem":"Expanded (SEM)",
        "n":"n_finished","n_total":"n_total","timeout_rate":"Timeout (%)"
    })
    xls = OUT_TABLES / "unsolv_summary.xlsx"
    with pd.ExcelWriter(xls, engine="xlsxwriter") as xw:
        tab.to_excel(xw, sheet_name="summary", index=False)
    print("✅", xls)

# ----------------------- main -----------------------

def main():
    per_board: Dict[str,pd.DataFrame] = {}
    for code, _ in BOARDS:
        per_board[code] = load_board(code)

    plot_runtime_and_expanded(per_board)
    plot_ratio_penalty(per_board)
    write_appendix_table(per_board)

if __name__ == "__main__":
    main()
