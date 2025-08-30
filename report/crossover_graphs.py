#!/usr/bin/env python3
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import glob, os

OUT = Path("report/figs"); OUT.mkdir(parents=True, exist_ok=True)

DOMAINS = ["p8","p15","r3x4","r3x5"]
LABELS  = {"p8":"P 8","p15":"P 15","r3x4":"R 3×4","r3x5":"R 3×5"}
COLORS  = {"p8":"#0072B2","p15":"#009E73","r3x4":"#56B4E9","r3x5":"#E69F00"}

TARGET_DEPTHS = list(range(4, 21, 2))          # even depths 4..20
OK_ALGOS = {"A*", "IDA*"}                      # exclude BPMX rows for 4.2

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

# ---------- file loading helpers ----------
def _collect_files(board: str) -> list[str]:
    """Gather every CSV for this board (merged, results, raw)."""
    pats = [
        f"results/merged/{board}.csv",
        f"results/{board}_*.csv",
        f"results/raw/*{board}*.csv",
    ]
    files = []
    for p in pats:
        files.extend(glob.glob(p))
    # stable order: merged first (usually newest), then others
    files = sorted(set(files), key=lambda s: (0 if "/merged/" in s else 1, s))
    return files

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # unify column names
    if "algo" in df.columns and "algorithm" not in df.columns:
        df = df.rename(columns={"algo":"algorithm"})
    if "time" in df.columns and "time_sec" not in df.columns:
        df = df.rename(columns={"time":"time_sec"})
    # most of our code expects these to exist
    for col in ["algorithm","heuristic","depth","time_sec","termination"]:
        if col not in df.columns:
            df[col] = np.nan
    return df

def _canon_heur(h: str) -> str:
    if h in ("linear", "linear_conflict", "lc"): return "linear_conflict"
    return "manhattan"

def load_curve(board: str, heur_in: str) -> pd.DataFrame | None:
    """Return grouped means/SEMs for A*, IDA* at even depths 4..20 for a board/heuristic."""
    heur = _canon_heur(heur_in)
    files = _collect_files(board)
    if not files:
        print(f"[load_curve] no files for {board}")
        return None

    frames = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
        except Exception:
            continue
        df = _normalize(df)
        # filter rows we actually want
        df = df[
            df["heuristic"].fillna("").eq(heur)
            & df["algorithm"].isin(OK_ALGOS)
            & df["termination"].fillna("ok").eq("ok")
        ]
        # keep only even depths 4..20
        df = df[df["depth"].isin(TARGET_DEPTHS)]
        if not df.empty:
            frames.append(df)

    if not frames:
        print(f"[load_curve] no rows after filtering for {board}/{heur}")
        return None

    df = pd.concat(frames, ignore_index=True)

    # coverage printout (helps debug missing points)
    haveA   = sorted(df.loc[df["algorithm"].eq("A*"),   "depth"].unique().tolist())
    haveIDA = sorted(df.loc[df["algorithm"].eq("IDA*"), "depth"].unique().tolist())
    missing = [d for d in TARGET_DEPTHS if (d not in haveA) or (d not in haveIDA)]
    if missing:
        print(f"[coverage] {LABELS[board]:5s}/{heur:15s} missing depths: {missing}")

    g = (df.groupby(["algorithm","depth"])
           .agg(time_sec_mean=("time_sec","mean"),
                time_sec_sem =("time_sec", sem))
           .reset_index())
    return g

def ratio_from_grouped(g: pd.DataFrame):
    a = g[g.algorithm=="A*"].set_index("depth")
    i = g[g.algorithm=="IDA*"].set_index("depth")
    common = sorted(a.index.intersection(i.index))
    if not common: return None
    ta, ti = a.loc[common,"time_sec_mean"].values, i.loc[common,"time_sec_mean"].values
    sa, si = a.loc[common,"time_sec_sem"].values,  i.loc[common,"time_sec_sem"].values
    r = ti/ta
    with np.errstate(divide="ignore", invalid="ignore"):
        rsem = np.sqrt((si/ti)**2 + (sa/ta)**2) * r
    return np.array(common), r, rsem

# ---------- (A) Common-depths plot ----------
def plot_crossover_common(heur="manhattan"):
    curves = {}
    for d in DOMAINS:
        g = load_curve(d, heur)
        if g is None: continue
        cur = ratio_from_grouped(g)
        if cur is not None: curves[d] = cur
    if not curves: return

    depth_sets = [set(x) for (x,_,_) in curves.values()]
    common = sorted(set.intersection(*depth_sets)) if len(depth_sets) > 1 else sorted(depth_sets[0])
    if not common: return

    plt.figure(figsize=(9.2,5.2))
    for d,(x,y,s) in curves.items():
        m = np.isin(x, common)
        plt.errorbar(x[m], y[m], yerr=s[m], marker="o", lw=2, capsize=3,
                     color=COLORS[d], label=LABELS[d])
    plt.axhline(1.0, ls=":", c="gray")
    plt.ylim(0.4, 1.4)
    plt.xlabel("Depth"); plt.ylabel("IDA*/A* time (↓ better for IDA*)")
    title_h = "Manhattan" if _canon_heur(heur)=="manhattan" else "Linear Conflict"
    plt.title(f"Crossover (IDA*/A*) across boards — {title_h} (common depths)")
    plt.legend(ncol=4, frameon=False)
    plt.tight_layout()
    out = OUT / f"crossover_all_{_canon_heur(heur)}_common.png"
    plt.savefig(out, dpi=200); plt.close()
    print("✅", out)

# ---------- (B) Union-of-depths plot ----------
def plot_crossover_union(heur="manhattan"):
    curves = {}
    all_depths = set()
    for d in DOMAINS:
        g = load_curve(d, heur)
        if g is None: continue
        cur = ratio_from_grouped(g)
        if cur is None: continue
        curves[d] = cur
        all_depths |= set(cur[0])

    if not curves: return
    common_depths = sorted(set.intersection(*[set(x) for (x,_,_) in curves.values()])) \
                    if len(curves) > 1 else sorted(list(all_depths))
    max_common = max(common_depths) if common_depths else None

    plt.figure(figsize=(9.2,5.2))
    for d,(x,y,s) in curves.items():
        plt.errorbar(x, y, yerr=s, marker="o", lw=2, capsize=3,
                     color=COLORS[d], label=LABELS[d], alpha=0.95)
    if max_common is not None and max(all_depths) > max_common:
        plt.axvspan(max_common+0.1, max(all_depths)+0.5, color="gray", alpha=0.08)
        plt.text(max_common+0.15, 1.36, "not all boards measured", fontsize=9, color="gray")
    plt.axhline(1.0, ls=":", c="gray")
    plt.ylim(0.4, 1.4)
    plt.xlabel("Depth"); plt.ylabel("IDA*/A* time (↓ better for IDA*)")
    title_h = "Manhattan" if _canon_heur(heur)=="manhattan" else "Linear Conflict"
    plt.title(f"Crossover (IDA*/A*) — {title_h} (union of depths)")
    plt.legend(ncol=4, frameon=False)
    plt.tight_layout()
    out = OUT / f"crossover_all_{_canon_heur(heur)}_union.png"
    plt.savefig(out, dpi=200); plt.close()
    print("✅", out)

# ---------- (C) 2×2 per-board grid ----------
def plot_ratio_grid():
    BLUE   = "#0072B2"   # Manhattan
    ORANGE = "#E69F00"   # Linear Conflict

    per = {}
    for d in DOMAINS:
        gm = load_curve(d, "manhattan")
        gl = load_curve(d, "linear_conflict")
        rm = ratio_from_grouped(gm) if gm is not None else None
        rl = ratio_from_grouped(gl) if gl is not None else None
        if (rm is None) and (rl is None): continue
        per[d] = (rm, rl)

    if not per: return
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 9.2), sharey=True)
    axes = axes.ravel()

    for ax, d in zip(axes, DOMAINS):
        if d not in per:
            ax.axis("off"); continue
        rm, rl = per[d]

        if rm is not None:
            x,y,s = rm
            ax.errorbar(x, y, yerr=s, marker="o", ms=5.5, lw=2.2, capsize=3,
                        color=BLUE, label="Manhattan", ls="-")
        if rl is not None:
            x,y,s = rl
            ax.errorbar(x, y, yerr=s, marker="^", ms=5.5, lw=2.2, capsize=3,
                        color=ORANGE, label="Linear", ls="--")

        ax.axhline(1.0, ls=":", c="gray")
        ax.set_title(LABELS[d])
        ax.set_xlabel("Depth"); ax.set_ylabel("IDA*/A* time (↓ better for IDA*)")
        ax.set_ylim(0.4, 1.6)
        ax.grid(True, alpha=0.2, ls=":")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.965))
    fig.suptitle("Crossover (IDA*/A*) per board — Manhattan (blue solid) vs Linear (orange dashed)",
                 fontsize=14, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    out = OUT / "crossover_ratio_grid.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print("✅", out)

if __name__ == "__main__":
    plot_crossover_common("manhattan")
    plot_crossover_union("manhattan")
    plot_ratio_grid()
