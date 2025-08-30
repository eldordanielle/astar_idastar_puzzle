#!/usr/bin/env python3
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import glob, re

OUT = Path("report/figs"); OUT.mkdir(parents=True, exist_ok=True)
RES = Path("results")

BOARDS  = ["p8","p15","r3x4","r3x5"]
LABELS  = {"p8":"P 8","p15":"P 15","r3x4":"R 3×4","r3x5":"R 3×5"}
HEURS   = ["manhattan","linear"]          # we’ll try to plot both
TARGET_DEPTHS = list(range(4, 21, 2))     # show 4..20 on the x-axis

# Okabe–Ito palette
BLUE   = "#0072B2"   # Man
ORANGE = "#E69F00"   # LC
GRAY   = "#7F7F7F"

# Color-blind–safe palette (Okabe–Ito)
# Strong, CVD-friendly mapping for the four boards
COLORS = {
    "p8":   "#0072B2",  # blue
    "p15":  "#009E73",  # bluish green
    "r3x4": "#D55E00",  # vermillion (more distinct than light blue)
    "r3x5": "#E69F00",  # orange
}
GRAY = "#7F7F7F"       # guide line

GRAY = "#7F7F7F"        # guide lines


EXCLUDE = re.compile(r"(unsolv|unsolvable|astar_vs_ida|smoke|sanity)", re.I)

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def _read_ok(p: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(p)
    except Exception:
        return None
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok")=="ok"]
    if "algorithm" not in df.columns or "depth" not in df.columns or "time_sec" not in df.columns:
        return None
    # only IDA*
    df = df[df["algorithm"].str.contains("IDA*", regex=False)]
    return df

# def find_files(board: str, heur: str, kind: str):
#     """kind in {'plain','bpmx'}."""
#     pats = []
#     tag = "_bpmx" if kind=="bpmx" else "_plain"
#     if board in ("r3x4","r3x5"):
#         # rectangles always include heuristic in filename
#         pats += [f"{board}_ida_{heur}{tag}*.csv"]
#     elif board == "p15":
#         if heur=="manhattan":
#             pats += [f"p15_ida{tag}*.csv"]  # manhattan runs often named without heuristic
#         else:
#             pats += [f"p15_ida_linear{tag}*.csv", f"p15_ida_linear_conflict{tag}*.csv"]
#     elif board == "p8":
#         if heur=="manhattan":
#             pats += [f"p8_ida{tag}*.csv", f"p8_ida_manhattan{tag}*.csv"]
#         else:
#             pats += [f"p8_ida_linear{tag}*.csv", f"p8_ida_linear_conflict{tag}*.csv"]

#     files = []
#     for pat in pats:
#         for p in glob.glob(str(RES/pat)):
#             if not EXCLUDE.search(Path(p).name):
#                 files.append(Path(p))
#     # unique, sorted
#     seen, out = set(), []
#     for p in sorted(files):
#         if p not in seen:
#             seen.add(p); out.append(p)
#     return out

def find_files(board: str, heur: str, kind: str):
    """Return a list of Paths (possibly empty). kind in {'plain','bpmx'}."""
    tag = "_bpmx" if kind == "bpmx" else "_plain"
    pats = []

    if board in ("r3x4", "r3x5"):
        # rectangles: heuristic always in filename
        pats += [f"{board}_ida_{heur}{tag}*.csv"]

    elif board == "p15":
        if heur == "manhattan":
            # support both naming styles:
            #  p15_ida_plain*.csv    (old)
            #  p15_ida_manhattan_plain*.csv  (your new files)
            pats += [f"p15_ida{tag}*.csv", f"p15_ida_manhattan{tag}*.csv"]
        else:
            pats += [f"p15_ida_linear{tag}*.csv", f"p15_ida_linear_conflict{tag}*.csv"]

    elif board == "p8":
        if heur == "manhattan":
            pats += [f"p8_ida{tag}*.csv", f"p8_ida_manhattan{tag}*.csv"]
        else:
            pats += [f"p8_ida_linear{tag}*.csv", f"p8_ida_linear_conflict{tag}*.csv"]

    files = []
    for pat in pats:
        for p in sorted((RES / pat).parent.glob((RES / pat).name)):
            if not EXCLUDE.search(p.name):
                files.append(p)

    return files  # ALWAYS return a list

# def aggregate(files):
#     frames = []
#     for p in files:
#         df = _read_ok(p)
#         if df is not None and not df.empty:
#             frames.append(df)
#     if not frames:
#         return None
#     df = pd.concat(frames, ignore_index=True)
#     g = (df.groupby("depth", as_index=False)
#            .agg(time_sec_mean=("time_sec","mean"),
#                 time_sec_sem =("time_sec", sem)))
#     return g.set_index("depth")

def aggregate(files):
    """Merge matching CSVs and return depth-indexed means/SEMs, or None if nothing found."""
    if not files:        # handles None and empty list
        return None
    frames = []
    for p in files:
        df = _read_ok(p)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    g = (df.groupby("depth", as_index=False)
           .agg(time_sec_mean=("time_sec", "mean"),
                time_sec_sem =("time_sec", sem)))
    return g.set_index("depth")


def ratio_curve(board, heur):
    P = aggregate(find_files(board, heur, "plain"))
    B = aggregate(find_files(board, heur, "bpmx"))
    if P is None or B is None:
        return None, None, None, []
    depths = sorted(set(P.index).intersection(B.index))
    if not depths:
        return None, None, None, []
    tp, sp = P.loc[depths,"time_sec_mean"].values, P.loc[depths,"time_sec_sem"].values
    tb, sb = B.loc[depths,"time_sec_mean"].values, B.loc[depths,"time_sec_sem"].values
    r = tb / tp
    with np.errstate(divide="ignore", invalid="ignore"):
        rsem = np.sqrt((sb/tb)**2 + (sp/tp)**2) * r
    missing = [d for d in TARGET_DEPTHS if d not in depths]
    return np.array(depths), r, rsem, missing

def coverage_report():
    print("\nBPMX ratio coverage report (need both Plain & BPMX):")
    for b in BOARDS:
        for h in HEURS:
            x,_,_,missing = ratio_curve(b,h)
            if x is None:
                print(f"  {LABELS[b]} / {h:<10}: MISSING (no matching file pairs)")
            else:
                print(f"  {LABELS[b]} / {h:<10}: depths={list(x)}  missing={missing}")

def plot_grid():
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.4), sharey=True, constrained_layout=False)
    axes = axes.ravel()
    for ax, b in zip(axes, BOARDS):
        # Manhattan
        xm, ym, sm, _ = ratio_curve(b,"manhattan")
        if xm is not None:
            ax.errorbar(xm, ym, yerr=sm, marker="o", ms=5.5, lw=2.2, capsize=3, color=BLUE,   ls="-",  label="Man")
        # Linear Conflict
        xl, yl, sl, _ = ratio_curve(b,"linear")
        if xl is not None:
            ax.errorbar(xl, yl, yerr=sl, marker="^", ms=5.5, lw=2.2, capsize=3, color=ORANGE, ls="--", label="LC")

        ax.axhline(1.0, ls=":", c=GRAY)
        ax.set_title(LABELS[b]); ax.set_xlabel("Depth"); ax.set_ylabel("BPMX/Plain time  (↓ < 1 helps)")
        ax.grid(True, alpha=0.25, ls=":")
        ax.set_xlim(4,20); ax.set_xticks(range(4,21,2))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=2, frameon=False)
    fig.suptitle("BPMX impact on IDA* — per board (ratio = timeBPMX / timePlain)", fontsize=16, y=0.995)
    fig.tight_layout(rect=[0,0,1,0.94])
    out = OUT / "bpmx_ratio_grid.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print("✅", out)

# def plot_common_manhattan():
#     curves = {}
#     for b in BOARDS:
#         x,y,s,_ = ratio_curve(b,"manhattan")
#         if x is not None:
#             curves[b] = (x,y,s)
#     if not curves:
#         print("No Manhattan BPMX data."); return
#     # common depths across boards where both Plain & BPMX exist
#     common = sorted(set.intersection(*[set(x) for (x,_,_) in curves.values()]))
#     if not common:
#         print("No common depths across boards."); return
#     plt.figure(figsize=(9.0,5.4))
#     for b,(x,y,s) in curves.items():
#         m = np.isin(x, common)
#         plt.errorbar(x[m], y[m], yerr=s[m], marker="o", lw=2.2, capsize=3, label=LABELS[b])
#     plt.axhline(1.0, ls=":", c=GRAY)
#     plt.xlabel("Depth"); plt.ylabel("BPMX/Plain time  (↓ < 1 helps)")
#     plt.title("BPMX impact on IDA* — Manhattan — across boards (common depths)")
#     plt.legend(ncol=len(curves), frameon=False)
#     plt.xlim(4,20); plt.xticks(range(4,21,2))
#     plt.ylim(0.9,1.1)
#     plt.tight_layout()
#     out = OUT / "bpmx_all_manhattan_common.png"
#     plt.savefig(out, dpi=200); plt.close()
#     print("✅", out)

def plot_common_manhattan():
    # collect curves
    curves = {}
    for b in BOARDS:
        x, y, s, _ = ratio_curve(b, "manhattan")
        if x is not None:
            if s is None:
                s = np.zeros_like(y)
            curves[b] = (x, y, s)

    if not curves:
        print("No Manhattan BPMX data."); return

    # common depths across all boards
    common = sorted(set.intersection(*[set(x) for (x,_,_) in curves.values()]))
    if not common:
        print("No common depths across boards."); return
    print("Common Manhattan depths across boards:", common)

    plt.figure(figsize=(9.0, 5.6))
    for b, (x, y, s) in curves.items():
        m = np.isin(x, common)
        # markers only (cleaner summary). If you prefer bars, add yerr=s[m], capsize=3.
        plt.plot(x[m], y[m], marker="o", lw=2.2, label=LABELS[b], color=COLORS[b])

    # ---- dynamic y-limits based on dot values (not error bars)
    all_y = np.concatenate([y[np.isin(x, common)] for (x, y, _) in curves.values()])
    pad = 0.015  # ~1.5% padding
    y_lo = float(np.nanmin(all_y)) - pad
    y_hi = float(np.nanmax(all_y)) + pad
    # keep a reasonable envelope
    y_lo = max(0.0, y_lo)   # don’t zoom too far down
    y_hi = min(2.0, y_hi)   # avoid huge empty space
    if y_hi <= y_lo:         # safety
        y_lo, y_hi = 0.95, 1.05
    plt.ylim(y_lo, y_hi)

    plt.axhline(1.0, ls=":", c=GRAY)
    plt.xlabel("Depth"); plt.ylabel("BPMX/Plain time  (↓ < 1 helps)")
    plt.title("BPMX impact on IDA* — Manhattan — across boards (common depths)")
    plt.legend(ncol=len(curves), frameon=False)
    plt.xlim(4, 20); plt.xticks(range(4, 21, 2))
    plt.tight_layout()

    out = OUT / "bpmx_all_manhattan_common.png"
    plt.savefig(out, dpi=200)
    plt.close()
    print("✅", out)


# --- put near your palettes ---
COLORS = {
    "p8":   "#0072B2",  # blue
    "p15":  "#009E73",  # bluish green
    "r3x4": "#D55E00",  # vermillion (more distinct than light blue)
    "r3x5": "#E69F00",  # orange
}
MARKERS = {"p8":"o", "p15":"s", "r3x4":"^", "r3x5":"D"}
GRAY = "#7F7F7F"

def plot_common_manhattan_clean(ymin=0.985, ymax=1.35, band=0.01, show_err=False):
    """
    Manhattan BPMX/Plain ratio at common depths across boards.
    - removes vertical vlines
    - adds a ±1% equivalence band around 1.0
    - right y-axis shows % overhead (no extra callouts)
    - legend includes mean overhead per board
    """
    # Collect curves for each board: x (depth), r (ratio), se (SEM of ratio)
    curves = {}
    for b in BOARDS:  # e.g., ["p8","p15","r3x4","r3x5"]
        x, r, se, _ = ratio_curve(b, "manhattan")
        if x is None: 
            continue
        if se is None:
            se = np.zeros_like(r)
        curves[b] = (np.asarray(x), np.asarray(r), np.asarray(se))

    if not curves:
        print("No Manhattan BPMX data."); 
        return

    # Common depths so every line spans the same x positions
    common = sorted(set.intersection(*[set(x) for (x,_,_) in curves.values()]))
    if not common:
        print("No common depths across boards."); 
        return

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10.5, 6.6))

    # Plot each board; add mean overhead in legend label
    for b, (x, r, se) in curves.items():
        m = np.isin(x, common)
        xd, rd, sed = x[m], r[m], se[m]
        mean_over = (np.nanmean(rd) - 1.0) * 100.0
        leg_label = f"{LABELS[b]} ({mean_over:+.2f}%)"
        if show_err:
            ax.errorbar(
                xd, rd, yerr=sed, capsize=3,
                marker=MARKERS[b], ms=6, lw=2.2,
                color=COLORS[b], label=leg_label
            )
        else:
            ax.plot(
                xd, rd, marker=MARKERS[b], ms=6, lw=2.2,
                color=COLORS[b], label=leg_label
            )

    # Reference line & practical-equivalence band
    ax.axhline(1.0, ls=":", c=GRAY)
    ax.fill_between([common[0], common[-1]], 1.0 - band, 1.0 + band,
                    color=GRAY, alpha=0.12, zorder=0)

    # Axes, ticks, labels
    ax.set_xlim(4, 20)
    ax.set_xticks(range(4, 21, 2))
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Depth")
    ax.set_ylabel("BPMX/Plain time  (↓ < 1 helps)")
    ax.set_title("BPMX impact on IDA* — Manhattan — across boards (common depths)")
    ax.grid(True, axis="y", alpha=0.25, linestyle=":")

    # Right y-axis in % overhead
    ax2 = ax.twinx()
    lo, hi = ax.get_ylim()
    ax2.set_ylim((lo - 1.0) * 100.0, (hi - 1.0) * 100.0)
    ax2.set_ylabel("% overhead vs plain IDA*  (negative would mean help)", labelpad=12)

    ax.legend(ncol=2, frameon=False, loc="upper left")
    fig.tight_layout()

    out = OUT / "bpmx_all_manhattan_common_clean.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("✅", out)

# if __name__ == "__main__":
#     coverage_report()
#     plot_grid()
#     plot_common_manhattan()

if __name__ == "__main__":
    coverage_report()
    plot_grid()                 # your per-board grid
    plot_common_manhattan()           # original ratio version (optional)
    plot_common_manhattan_clean()   # NEW: % speedup version
