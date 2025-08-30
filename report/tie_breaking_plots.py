#!/usr/bin/env python3
import argparse, os, re, glob
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_FIGS   = Path("report/figs");   OUT_FIGS.mkdir(parents=True, exist_ok=True)
OUT_TABLES = Path("report/tables"); OUT_TABLES.mkdir(parents=True, exist_ok=True)

OKABE = {
    "h":    "#0072B2",  # blue
    "g":    "#E69F00",  # orange
    "fifo": "#009E73",  # green
    "lifo": "#CC79A7",  # purple
}
ORDER = ["h","g","fifo","lifo"]
LABEL = {"h":"h (prefer smaller h)",
         "g":"g (prefer smaller g)",
         "fifo":"fifo (older first)",
         "lifo":"lifo (newer first)"}

HEUR_ALIASES = {
    "manhattan": ["manhattan"],
    "linear":    ["linear","linear_conflict"],
}

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1)/np.sqrt(n)

def infer_tie_from_name(name: str) -> str | None:
    m = re.search(r"_tie_(h|g|fifo|lifo)", name)
    return m.group(1) if m else None

def find_files(board: str, heur_key: str) -> list[Path]:
    pats = [
        f"results/{board}_tie_*.csv",
        f"results/{board}_*_tie_*.csv",
        f"results/**/*{board}*_tie_*.csv",
    ]
    cand = []
    for pat in pats:
        cand.extend(Path(p) for p in glob.glob(pat, recursive=True))
    # Heuristic filter by filename (broad): keep files that mention our heuristic alias (if present)
    aliases = HEUR_ALIASES.get(heur_key, [heur_key])
    def keep(p: Path) -> bool:
        s = p.name.lower()
        # if the file mentions a heuristic, require it to match our aliases; otherwise accept
        mentions = any(h in s for h in ["manhattan","linear","linear_conflict"])
        return (not mentions) or any(a in s for a in aliases)
    uniq = []
    seen = set()
    for p in sorted(set(cand)):
        if keep(p) and p.exists() and p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def load_agg(paths: list[Path], heur_key: str) -> pd.DataFrame:
    rows = []
    for p in paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if "algorithm" not in df or "depth" not in df or "time_sec" not in df:
            continue
        # A* only, finished only
        df = df[(df["algorithm"]=="A*") & (df["termination"].fillna("ok")=="ok")].copy()
        # heuristic filter if column exists
        if "heuristic" in df.columns:
            aliases = HEUR_ALIASES.get(heur_key, [heur_key])
            mask = df["heuristic"].astype(str).str.lower().apply(
                lambda s: any(a in s for a in aliases)
            )
            df = df[mask]
        if df.empty: 
            continue
        # tie_break column (fallback to filename)
        if "tie_break" not in df.columns or df["tie_break"].isna().all():
            tie = infer_tie_from_name(p.name)
            if tie is None: 
                continue
            df = df.copy()
            df["tie_break"] = tie
        # only supported ties
        df = df[df["tie_break"].isin(ORDER)]
        if "duplicates" not in df.columns:
            df["duplicates"] = np.nan
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    df = pd.concat(rows, ignore_index=True).drop_duplicates()
    g = (df.groupby(["depth","tie_break"], as_index=False)
            .agg(time_mean=("time_sec","mean"),
                 time_sem =("time_sec", sem),
                 dup_mean =("duplicates","mean"),
                 dup_sem  =("duplicates", sem),
                 n=("time_sec","count")))
    # consistent ordering
    g["tie_break"] = pd.Categorical(g["tie_break"], ORDER, ordered=True)
    g = g.sort_values(["depth","tie_break"]).reset_index(drop=True)
    return g

def spread_median_pct(g: pd.DataFrame, col: str) -> float:
    """Median across depths of (max/min - 1)*100 for metric 'col'."""
    vals = []
    for d, part in g.groupby("depth"):
        v = part[col].to_numpy()
        v = v[np.isfinite(v)]
        if len(v) >= 2 and np.min(v) > 0:
            vals.append((np.max(v)/np.min(v) - 1.0)*100.0)
    return float(np.median(vals)) if vals else float("nan")

def plot(g: pd.DataFrame, board_label: str, heur_label: str, out_png: Path, out_xlsx: Path):
    if g.empty:
        print("No data to plot.")
        return
    depths = sorted(g["depth"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), sharex=True)
    axT, axD = axes

    for tie in ORDER:
        part = g[g["tie_break"]==tie]
        if part.empty: continue
        axT.errorbar(part["depth"], part["time_mean"], yerr=part["time_sem"],
                     label=LABEL[tie], color=OKABE[tie], marker="o", lw=2, capsize=3)
        axD.errorbar(part["depth"], part["dup_mean"], yerr=part["dup_sem"],
                     label=LABEL[tie], color=OKABE[tie], marker="^", lw=2, capsize=3, ls="--")

    for ax in axes:
        ax.set_xticks(depths)
        ax.grid(True, alpha=0.25, ls=":")
        ax.set_xlabel("Depth")

    axT.set_ylabel("Time (s)")
    axD.set_ylabel("Duplicates (mean)")

    fig.suptitle(f"A* tie-breaking ablation — {board_label} ({heur_label})", y=0.93)
    handles, labels = axT.get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=[0,0,1,0.93])
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print("✅", out_png)

    # Write appendix table (per-depth mean ± SEM)
    tbl = g.rename(columns={
        "depth":"Depth","tie_break":"Tie","time_mean":"Time (s, mean)",
        "time_sem":"Time (s, SEM)","dup_mean":"Duplicates (mean)",
        "dup_sem":"Duplicates (SEM)","n":"n"
    })
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as xw:
        tbl.to_excel(xw, sheet_name="tiebreak_summary", index=False)
    print("✅", out_xlsx)

    # Quick deltas to paste in text
    dt = spread_median_pct(g, "time_mean")
    dd = spread_median_pct(g, "dup_mean")
    print(f"≈ Median tie-break spread — time: {dt:.1f}%, duplicates: {dd:.1f}%")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="p15", help="p8 | p15 | r3x4 | r3x5")
    ap.add_argument("--heur",  default="manhattan", help="manhattan | linear")
    args = ap.parse_args()

    board_label = {"p8":"P 8","p15":"P 15","r3x4":"R 3×4","r3x5":"R 3×5"}.get(args.board, args.board)
    heur_label  = "Manhattan" if args.heur=="manhattan" else "Linear Conflict"

    files = find_files(args.board, args.heur)
    print(f"Found {len(files)} candidate files.")
    g = load_agg(files, args.heur)

    out_png  = OUT_FIGS   / f"tiebreak_{args.board}_{args.heur}.png"
    out_xlsx = OUT_TABLES / f"tiebreak_{args.board}_{args.heur}.xlsx"
    plot(g, board_label, heur_label, out_png, out_xlsx)

if __name__ == "__main__":
    main()
