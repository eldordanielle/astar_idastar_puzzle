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

BOARDS   = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]
HEURS_IN = {"manhattan":["manhattan"], "linear":["linear","linear_conflict"]}  # accept either file naming
HEURS_SH = {"manhattan":"Man", "linear":"LC"}

EXCLUDE = ("bpmx", "unsolv", "unsolvable", "astar_vs_ida", "smoke", "sanity")

EVEN_DEPTHS = list(range(4, 22, 2))

def find_files(board: str, heur_key: str) -> list[Path]:
    pats = []
    for h in HEURS_IN[heur_key]:
        pats += [
            f"results/{board}_{h}.csv",
            f"results/{board}_{h}_*.csv",
            f"results/{board}_*_{h}.csv",
            f"results/{board}_*_{h}_*.csv",
        ]
    out = []
    for pat in pats:
        for p in glob.glob(pat):
            name = os.path.basename(p).lower()
            if any(tag in name for tag in EXCLUDE):
                continue
            out.append(Path(p))
    # unique, stable
    seen, uniq = set(), []
    for p in sorted(out):
        if p not in seen:
            seen.add(p); uniq.append(p)
    return uniq

def load_ok(p: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    need = {"algorithm","depth","time_sec"}
    if not need.issubset(df.columns):
        return None
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok")=="ok"]
    df = df[df["algorithm"].isin(["A*","IDA*"])]
    return df if not df.empty else None

def geometric_mean(arr):
    arr = np.asarray(arr, float)
    arr = arr[~np.isnan(arr)]
    return np.exp(np.mean(np.log(arr))) if len(arr) else np.nan

def ratio_series(df: pd.DataFrame) -> pd.DataFrame | None:
    """Return per-depth IDA*/A* time ratio on common depths present in both algos and in EVEN_DEPTHS."""
    a = df[df["algorithm"]=="A*"].groupby("depth")["time_sec"].mean()
    i = df[df["algorithm"]=="IDA*"].groupby("depth")["time_sec"].mean()
    common = sorted(set(a.index).intersection(i.index).intersection(EVEN_DEPTHS))
    if not common:
        return None
    r = (i.loc[common] / a.loc[common]).rename("ratio").reset_index()
    return r  # columns: depth, ratio

def main():
    rows = []   # one row per (board, heur) with aggregate metrics
    curves = {} # optional: store the per-depth ratios for debugging/appendix

    for b_code, b_label in BOARDS:
        for h_key in ("manhattan","linear"):
            files = find_files(b_code, h_key)
            dfs = []
            for p in files:
                d = load_ok(p)
                if d is not None: dfs.append(d)
            if not dfs:
                continue
            df = pd.concat(dfs, ignore_index=True).drop_duplicates()
            r = ratio_series(df)
            if r is None or r.empty:
                continue

            # aggregate across depths
            gm = geometric_mean(r["ratio"].values)     # overall ratio across common depths
            frac_ida = float(np.mean(r["ratio"].values <= 1.0))  # fraction of depths with IDA* <= A*
            first_cross = next((int(d) for d, val in zip(r["depth"], r["ratio"]) if val >= 1.0), None)

            rows.append({
                "Board": b_label,
                "Heur": HEURS_SH[h_key],
                "geo_mean_ratio": gm,
                "frac_ida_faster": frac_ida,
                "first_cross_depth": first_cross
            })
            curves[(b_label, HEURS_SH[h_key])] = r

    if not rows:
        raise SystemExit("No (board,heur) pairs with usable data found.")

    summ = pd.DataFrame(rows)
    # ---- figure: bars (geo-mean ratio) + bars (fraction IDA* wins)
    # color-blind friendly: Okabe–Ito
    C_MAN = "#0072B2"  # blue
    C_LC  = "#E69F00"  # orange

    # consistent board order
    board_order = ["P 8","P 15","R 3×4","R 3×5"]
    summ["Board"] = pd.Categorical(summ["Board"], board_order, ordered=True)
    summ["Heur"]  = pd.Categorical(summ["Heur"], ["Man","LC"], ordered=True)
    summ = summ.sort_values(["Board","Heur"]).reset_index(drop=True)

    # plotting
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    # left: geometric mean ratio (IDA*/A*)
    x_pos = np.arange(len(board_order))
    width = 0.36

    # arrays per heur
    def pick(col, heur):
        return [summ[(summ.Board==b)&(summ.Heur==heur)][col].values[0] if not summ[(summ.Board==b)&(summ.Heur==heur)][col].empty else np.nan
                for b in board_order]

    man_vals = pick("geo_mean_ratio","Man")
    lc_vals  = pick("geo_mean_ratio","LC")

    axes[0].bar(x_pos - width/2, man_vals, width, label="Man", color=C_MAN)
    axes[0].bar(x_pos + width/2, lc_vals,  width, label="LC",  color=C_LC)
    axes[0].axhline(1.0, color="gray", ls=":")
    axes[0].set_xticks(x_pos, board_order)
    axes[0].set_ylabel("IDA*/A* time (geo-mean across depths)")
    axes[0].set_title("Overall speed ratio (lower < 1 favors IDA*)")
    axes[0].set_ylim(0.5, max(1.25, np.nanmax([man_vals, lc_vals]) * 1.1))
    axes[0].grid(True, axis="y", alpha=0.25, ls=":")

    # right: fraction of depths with IDA* <= A*
    man_frac = pick("frac_ida_faster","Man")
    lc_frac  = pick("frac_ida_faster","LC")
    axes[1].bar(x_pos - width/2, man_frac, width, label="Man", color=C_MAN)
    axes[1].bar(x_pos + width/2, lc_frac,  width, label="LC",  color=C_LC)
    axes[1].axhline(0.5, color="gray", ls=":", lw=1)
    axes[1].set_xticks(x_pos, board_order)
    axes[1].set_ylabel("Fraction of depths with IDA* faster")
    axes[1].set_title("Win-fraction across common depths (4…20)")
    axes[1].set_ylim(0, 1)
    axes[1].grid(True, axis="y", alpha=0.25, ls=":")

    # shared legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Cross-puzzle summary — A* vs IDA* (Manhattan vs LC)", y=1.06, fontsize=14)
    fig.tight_layout()

    out = OUT / "cross_puzzle_summary.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("✅", out)

if __name__ == "__main__":
    main()
