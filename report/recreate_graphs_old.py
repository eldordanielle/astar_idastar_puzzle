#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ========================= Config =========================
FIGS = Path("report/figs"); FIGS.mkdir(parents=True, exist_ok=True)

FIGSIZE = (16, 8.4)
GRID_TOP, GRID_BOTTOM, GRID_LEFT, GRID_RIGHT, GRID_WSPACE = 0.86, 0.12, 0.06, 0.985, 0.28
TITLE_Y, LEGEND_Y = 0.975, 0.91

GRID_ROW_HEIGHT = 8.4   # try 7.2–9.0 if you want slightly shorter/taller


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
    "font.size": 13, "axes.titlesize": 16, "axes.labelsize": 14,
    "xtick.labelsize": 12, "ytick.labelsize": 12,
})

HEUR_LABEL = {"manhattan": "Manhattan", "linear": "Linear Conflict"}
DOM_LABEL  = {"p8": "8-puzzle", "p15": "15-puzzle", "r3x4": "3×4 rectangle", "r3x5": "3×5 rectangle"}

# ========================= Utils =========================
def exists(p: Path) -> bool:
    try: return p.exists()
    except Exception: return False

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

    out = (df.groupby(["algorithm", "depth"], as_index=False)
             .agg({m: ["mean", sem] for m in metrics}))
    out.columns = ["algorithm", "depth"] + [f"{m}_{k}" for m in metrics for k in ("mean","sem")]
    return out.sort_values(["algorithm", "depth"])

def add_series(ax, data: pd.DataFrame, algo_label: str, x="depth", y="value", yerr="sem"):
    ax.errorbar(data[x], data[y], yerr=data[yerr], capsize=3, elinewidth=1.3, **STYLES[algo_label])

def layout_with_title_and_legend(title: str):
    fig = plt.figure(figsize=FIGSIZE, constrained_layout=False)
    gs = fig.add_gridspec(1, 3, left=GRID_LEFT, right=GRID_RIGHT, bottom=GRID_BOTTOM,
                          top=GRID_TOP, wspace=GRID_WSPACE)
    ax1, ax2, ax3 = (fig.add_subplot(gs[0, i]) for i in range(3))
    fig.suptitle(title, fontsize=24, fontweight="bold", y=TITLE_Y)
    return fig, (ax1, ax2, ax3)

def finalize_axes(ax, xlab, ylab):
    ax.set_xlabel(xlab); ax.set_ylabel(ylab)
    ax.grid(True, alpha=0.25, linestyle=":")

def put_legend(fig, labels_present):
    order = ["A*","IDA*","IDA*+BPMX"]
    labels = [l for l in order if l in labels_present]
    handles = [plt.Line2D([0],[0], **STYLES[l], label=l) for l in labels]
    if labels:
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, LEGEND_Y),
                   ncol=len(labels), frameon=False)

# ========================= Generic plotters =========================
def make_plot(df_main: pd.DataFrame, title: str, out_path: Path,
              add_bpmx: pd.DataFrame | None = None):
    fig, (ax1, ax2, ax3) = layout_with_title_and_legend(title)
    labels_present = set()

    def plot_algo(ax, df_src, algo_name, metric):
        cur = df_src[df_src["algorithm"] == algo_name]
        if cur.empty: return False
        d = cur[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
        d.columns = ["depth", "value", "sem"]
        add_series(ax, d, algo_name)
        return True

    def draw_metric(ax, metric, ylab):
        if plot_algo(ax, df_main, "A*", metric):   labels_present.add("A*")
        if plot_algo(ax, df_main, "IDA*", metric): labels_present.add("IDA*")
        # Prefer BPMX from main df; else use overlay
        plotted = plot_algo(ax, df_main, "IDA*+BPMX", metric)
        if (not plotted) and (add_bpmx is not None) and (not add_bpmx.empty):
            b = add_bpmx[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
            b.columns = ["depth","value","sem"]
            add_series(ax, b, "IDA*+BPMX"); labels_present.add("IDA*+BPMX")
        elif plotted:
            labels_present.add("IDA*+BPMX")
        finalize_axes(ax, "Depth", ylab)

    draw_metric(ax1, "expanded",  "expanded")
    draw_metric(ax2, "generated", "generated")
    draw_metric(ax3, "time_sec",  "seconds")

    put_legend(fig, labels_present)
    fig.savefig(out_path, dpi=200); plt.close(fig)
    print(f"✅ {out_path}")

# def maybe_bpmx_overlay(domain: str) -> pd.DataFrame | None:
#     """Build an overlay DataFrame for IDA*+BPMX if we have paired runs."""
#     plain = Path(f"results/{domain}_ida_plain.csv")
#     bpmx  = Path(f"results/{domain}_ida_bpmx.csv")
#     if exists(plain) and exists(bpmx):
#         ida_plain = aggregate(load_ok(plain))
#         ida_bpmx  = aggregate(load_ok(bpmx))
#         common = sorted(set(ida_plain["depth"]).intersection(set(ida_bpmx["depth"])))
#         add_b = ida_bpmx[ida_bpmx["depth"].isin(common)].copy()
#         add_b["algorithm"] = "IDA*+BPMX"
#         return add_b
#     return None

# def _first_existing(paths: list[Path]) -> Path | None:
#     for p in paths:
#         if exists(p):  # your safe exists()
#             return p
#     return None

def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if exists(p):
            return p
    return None

def maybe_bpmx_overlay(domain: str, heur: str | None = None) -> pd.DataFrame | None:
    """
    Accepts any of these pairs (plain/bpmx), in priority order:
      results/{domain}_{heur}_ida_plain.csv   & results/{domain}_{heur}_ida_bpmx.csv
      results/{domain}_ida_{heur}_plain.csv   & results/{domain}_ida_{heur}_bpmx.csv
      results/{domain}_ida_plain.csv          & results/{domain}_ida_bpmx.csv
    Also treats 'linear' and 'linear_conflict' as synonyms.
    """
    heur_aliases = []
    if heur:
        heur_aliases = [heur]
        if heur == "linear" or heur == "linear_conflict":
            heur_aliases = ["linear", "linear_conflict"]

    plain_candidates, bpmx_candidates = [], []

    for h in (heur_aliases or [None]):
        if h is not None:
            # domain–heur–ida and domain–ida–heur
            plain_candidates += [
                Path(f"results/{domain}_{h}_ida_plain.csv"),
                Path(f"results/{domain}_ida_{h}_plain.csv"),
            ]
            bpmx_candidates += [
                Path(f"results/{domain}_{h}_ida_bpmx.csv"),
                Path(f"results/{domain}_ida_{h}_bpmx.csv"),
            ]

    # domain-only fallback
    plain_candidates += [Path(f"results/{domain}_ida_plain.csv")]
    bpmx_candidates  += [Path(f"results/{domain}_ida_bpmx.csv")]

    plain = _first_existing(plain_candidates)
    bpmx  = _first_existing(bpmx_candidates)
    if not (plain and bpmx):
        return None

    ida_plain = aggregate(load_ok(plain))
    ida_bpmx  = aggregate(load_ok(bpmx))
    common = sorted(set(ida_plain["depth"]).intersection(set(ida_bpmx["depth"])))
    if not common:
        return None

    add_b = ida_bpmx[ida_bpmx["depth"].isin(common)].copy()
    add_b["algorithm"] = "IDA*+BPMX"
    return add_b

def load_domain_heu(domain: str, heur: str) -> pd.DataFrame | None:
    p = Path(f"results/{domain}_{heur}.csv")
    if not exists(p): return None
    return aggregate(load_ok(p))

# ========================= Figure builders =========================
# def build_per_depth(domain: str, heur: str):
#     df = load_domain_heu(domain, heur)
#     if df is None: return
#     overlay = maybe_bpmx_overlay(domain)  # will be used only if BPMX missing in df
#     title = f"{DOM_LABEL.get(domain, domain)} ({HEUR_LABEL.get(heur, heur)}) — per-depth curves"
#     out   = FIGS / f"{domain}_{heur}_full_combined.png"
#     make_plot(df, title=title, out_path=out, add_bpmx=overlay)

def build_per_depth(domain: str, heur: str):
    df = load_domain_heu(domain, heur)
    if df is None:
        return
    overlay = maybe_bpmx_overlay(domain, heur)  # <— now heuristic-aware
    title = f"{DOM_LABEL.get(domain, domain)} ({HEUR_LABEL.get(heur, heur)}) — per-depth curves"
    out   = FIGS / f"{domain}_{heur}_full_combined.png"
    make_plot(df, title=title, out_path=out, add_bpmx=overlay)

def build_crossover_ratio(domain: str, heur: str):
    df = load_domain_heu(domain, heur)
    if df is None: return
    a = df[df["algorithm"]=="A*"][["depth","time_sec_mean"]].set_index("depth")
    i = df[df["algorithm"]=="IDA*"][["depth","time_sec_mean"]].set_index("depth")
    common = sorted(set(a.index).intersection(i.index))
    if not common: return
    ratio = (i.loc[common,"time_sec_mean"] / a.loc[common,"time_sec_mean"]).rename("ratio")
    sem_a = df[df["algorithm"]=="A*"][["depth","time_sec_sem"]].set_index("depth").loc[common,"time_sec_sem"]
    sem_i = df[df["algorithm"]=="IDA*"][["depth","time_sec_sem"]].set_index("depth").loc[common,"time_sec_sem"]
    # conservative SEM for ratio via propagation (approx)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = (sem_i/i.loc[common,"time_sec_mean"])**2 + (sem_a/a.loc[common,"time_sec_mean"])**2
        sem_ratio = np.sqrt(rel) * ratio.values
    fig, ax = plt.subplots(figsize=(8,5))
    ax.errorbar(common, ratio.values, yerr=sem_ratio, **STYLES["IDA*"], capsize=3, elinewidth=1.3)
    ax.axhline(1.0, linestyle=":", color="gray", lw=1)
    ax.set_title(f"Crossover (IDA*/A*) — {DOM_LABEL.get(domain,domain)} ({HEUR_LABEL.get(heur,heur)})")
    ax.set_xlabel("Depth"); ax.set_ylabel("time ratio (IDA*/A*)"); ax.grid(True, alpha=0.25, linestyle=":")
    out = FIGS / f"crossover_{domain}_{heur}.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print(f"✅ {out}")

def build_bpmx_ratio(domain: str):
    overlay = maybe_bpmx_overlay(domain)
    if overlay is None: return
    plain = Path(f"results/{domain}_ida_plain.csv")
    ida_plain = aggregate(load_ok(plain))
    # align on common depths
    common = sorted(set(overlay["depth"]).intersection(set(ida_plain["depth"])))
    if not common: return
    t_b = overlay.set_index("depth").loc[common,"time_sec_mean"]
    t_p = ida_plain.set_index("depth").loc[common,"time_sec_mean"]
    ratio = (t_b / t_p).rename("ratio")
    # rough SEM for ratio:
    sb = overlay.set_index("depth").loc[common,"time_sec_sem"]
    sp = ida_plain.set_index("depth").loc[common,"time_sec_sem"]
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = (sb/t_b)**2 + (sp/t_p)**2
        sem_ratio = np.sqrt(rel) * ratio.values
    fig, ax = plt.subplots(figsize=(8,5))
    ax.errorbar(common, ratio.values, yerr=sem_ratio, **STYLES["IDA*+BPMX"], capsize=3, elinewidth=1.3)
    ax.axhline(1.0, linestyle=":", color="gray", lw=1)
    ax.set_title(f"BPMX effect (BPMX/Plain, IDA*) — {DOM_LABEL.get(domain,domain)}")
    ax.set_xlabel("Depth"); ax.set_ylabel("time ratio (BPMX / Plain)"); ax.grid(True, alpha=0.25, linestyle=":")
    out = FIGS / f"bpmx_ratio_{domain}.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print(f"✅ {out}")

def build_unsolv_vs_solv_p8():
    """
    Looks for either:
      - results/p8_unsolved.csv & results/p8_solved.csv
      - OR a single results/p8_manhattan.csv with a boolean 'solvable' column.
    Produces: report/figs/p8_unsolv_vs_solv_combo.png
    """
    left_label, right_label = "seconds (log)", "generated (log)"
    out = FIGS / "p8_unsolv_vs_solv_combo.png"

    # Try separate files first
    p_uns = Path("results/p8_unsolved.csv"); p_sol = Path("results/p8_solved.csv")
    if exists(p_uns) and exists(p_sol):
        du, ds = aggregate(load_ok(p_uns)), aggregate(load_ok(p_sol))
    else:
        # Try single CSV with flag
        df = load_domain_heu("p8", "manhattan")
        if df is None: return
        # Can't derive solvability post-aggregation; try raw file with flag:
        raw = Path("results/p8_manhattan.csv")
        if not exists(raw): return
        raw_df = load_ok(raw)
        if "solvable" not in raw_df.columns and "is_solvable" not in raw_df.columns: return
        flag = "solvable" if "solvable" in raw_df.columns else "is_solvable"
        du = aggregate(raw_df[raw_df[flag]==False])
        ds = aggregate(raw_df[raw_df[flag]==True])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.2))
    # TIME
    for lbl, dfc, style in [("unsolvable", du, "IDA*"), ("solvable", ds, "A*")]:
        if not dfc.empty:
            t = dfc[dfc["algorithm"].isin(["A*","IDA*"])][["algorithm","depth","time_sec_mean","time_sec_sem"]]
            for algo in ["A*","IDA*"]:
                tt = t[t["algorithm"]==algo][["depth","time_sec_mean","time_sec_sem"]]
                if tt.empty: continue
                dd = tt.rename(columns={"time_sec_mean":"value","time_sec_sem":"sem"})
                add_series(ax1, dd, algo)
    ax1.set_yscale("log"); ax1.set_xlabel("Depth"); ax1.set_ylabel(left_label); ax1.grid(True, alpha=0.25, linestyle=":")

    # GENERATED
    for lbl, dfc in [("unsolvable", du), ("solvable", ds)]:
        if not dfc.empty:
            g = dfc[dfc["algorithm"].isin(["A*","IDA*"])][["algorithm","depth","generated_mean","generated_sem"]]
            for algo in ["A*","IDA*"]:
                gg = g[g["algorithm"]==algo][["depth","generated_mean","generated_sem"]]
                if gg.empty: continue
                dd = gg.rename(columns={"generated_mean":"value","generated_sem":"sem"})
                add_series(ax2, dd, algo)
    ax2.set_yscale("log"); ax2.set_xlabel("Depth"); ax2.set_ylabel(right_label); ax2.grid(True, alpha=0.25, linestyle=":")

    fig.suptitle("8-puzzle — solvable vs unsolvable", fontsize=20, y=0.98)
    put_legend(fig, {"A*","IDA*"})
    fig.savefig(out, dpi=200); plt.close(fig)
    print(f"✅ {out}")

# --- Add after your existing helpers ---

HEUR_KEYS = [("manhattan", "Manhattan"),
             ("linear", "Linear Conflict"),
             ("linear_conflict", "Linear Conflict")]  # alias support

def _load_heur_df(domain: str, heur_key: str) -> pd.DataFrame | None:
    # tries results/{domain}_{heur}.csv first; falls back to {domain}_{alias}.csv
    p = Path(f"results/{domain}_{heur_key}.csv")
    if exists(p):
        return aggregate(load_ok(p))
    # accept r3x* files that used 'linear' instead of 'linear_conflict' or vice versa
    if heur_key == "linear":
        alt = Path(f"results/{domain}_linear_conflict.csv")
        if exists(alt): return aggregate(load_ok(alt))
    if heur_key == "linear_conflict":
        alt = Path(f"results/{domain}_linear.csv")
        if exists(alt): return aggregate(load_ok(alt))
    return None

def _maybe_bpmx_overlay_any(domain: str, heur_key: str) -> pd.DataFrame | None:
    # Accept both orderings and aliases (domain_{heur}_ida_* and domain_ida_{heur}_*)
    heur_aliases = [heur_key]
    if heur_key in ("linear", "linear_conflict"):
        heur_aliases = ["linear", "linear_conflict"]

    cand_plain, cand_bpmx = [], []
    for h in heur_aliases:
        cand_plain += [Path(f"results/{domain}_{h}_ida_plain.csv"),
                       Path(f"results/{domain}_ida_{h}_plain.csv")]
        cand_bpmx  += [Path(f"results/{domain}_{h}_ida_bpmx.csv"),
                       Path(f"results/{domain}_ida_{h}_bpmx.csv")]
    # domain-only fallback
    cand_plain += [Path(f"results/{domain}_ida_plain.csv")]
    cand_bpmx  += [Path(f"results/{domain}_ida_bpmx.csv")]

    def first_ok(xx): 
        return next((p for p in xx if exists(p)), None)

    p_plain, p_bpmx = first_ok(cand_plain), first_ok(cand_bpmx)
    if not (p_plain and p_bpmx): return None

    ida_plain = aggregate(load_ok(p_plain))
    ida_bpmx  = aggregate(load_ok(p_bpmx))
    common = sorted(set(ida_bpmx["depth"]).intersection(set(ida_plain["depth"])))
    if not common: return None
    out = ida_bpmx[ida_bpmx["depth"].isin(common)].copy()
    out["algorithm"] = "IDA*+BPMX"
    return out

def build_board_grid(domain: str):
    """
    Makes one figure: rows = [Manhattan, Linear Conflict], cols = [expanded, generated, time].
    Saves to report/figs/{domain}_grid_full.png
    """
    # collect data per heuristic
    rows = []
    for heur_key, heur_title in [("manhattan","Manhattan"), ("linear","Linear Conflict")]:
        df = _load_heur_df(domain, heur_key)
        if df is None:
            continue
        overlay = _maybe_bpmx_overlay_any(domain, heur_key)
        rows.append((heur_title, df, overlay))

    if not rows:
        return  # nothing to draw

    # figure layout: 2x3 (or 1x3 if only one heuristic)
    nrows = len(rows)
    fig_h = GRID_ROW_HEIGHT * nrows
    # fig = plt.figure(figsize=(16, 5.2*nrows), constrained_layout=False)
    fig = plt.figure(figsize=(16, fig_h), constrained_layout=False)
    gs = fig.add_gridspec(nrows, 3, left=GRID_LEFT, right=GRID_RIGHT,
                          bottom=GRID_BOTTOM, top=GRID_TOP, wspace=GRID_WSPACE, hspace=0.38)

    labels_present = set()
    def plot_cell(ax, df_main, overlay, metric, ylab):
        def plot_algo(df_src, algo):
            cur = df_src[df_src["algorithm"] == algo]
            if cur.empty: return False
            d = cur[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
            d.columns = ["depth","value","sem"]
            add_series(ax, d, algo)
            return True
        if plot_algo(df_main, "A*"): labels_present.add("A*")
        if plot_algo(df_main, "IDA*"): labels_present.add("IDA*")
        plotted_b = plot_algo(df_main, "IDA*+BPMX")
        if (not plotted_b) and (overlay is not None) and (not overlay.empty):
            b = overlay[["depth", f"{metric}_mean", f"{metric}_sem"]].copy()
            b.columns = ["depth","value","sem"]
            add_series(ax, b, "IDA*+BPMX")
            labels_present.add("IDA*+BPMX")
        elif plotted_b:
            labels_present.add("IDA*+BPMX")
        finalize_axes(ax, "Depth", ylab)

    for r, (heur_title, dfh, ov) in enumerate(rows):
        ax_exp = fig.add_subplot(gs[r, 0]); plot_cell(ax_exp, dfh, ov, "expanded",  "expanded")
        ax_gen = fig.add_subplot(gs[r, 1]); plot_cell(ax_gen, dfh, ov, "generated", "generated")
        ax_tim = fig.add_subplot(gs[r, 2]); plot_cell(ax_tim, dfh, ov, "time_sec",  "seconds")
        ax_exp.set_title(heur_title, fontsize=16, pad=8)  # row label on first column

    fig.suptitle(f"{domain.upper().replace('P','P ').replace('R','R ')} — per-depth (Manhattan vs Linear Conflict)",
                 fontsize=24, fontweight="bold", y=TITLE_Y)
    put_legend(fig, labels_present)
    out = FIGS / f"{domain}_grid_full.png"
    fig.savefig(out, dpi=200); plt.close(fig)
    print(f"✅ {out}")


# ========================= Main build =========================
def main():
    # Per-depth curves (Manhattan + Linear Conflict) for p8 & p15
    for dom in ["p8", "p15"]:
        for heur in ["manhattan", "linear"]:
            build_per_depth(dom, heur)

    # Rectangles (Manhattan only by default; add 'linear' if you have CSVs)
    for dom in ["r3x4", "r3x5"]:
        for heur in ["manhattan", "linear"]:
            build_per_depth(dom, heur)

    # Crossover ratios (IDA*/A*) — commonly needed for p15 + r3x5
    for dom, heur in [("p15","manhattan"), ("p15","linear"), ("r3x5","manhattan")]:
        build_crossover_ratio(dom, heur)

    # BPMX effect ratio (BPMX/Plain for IDA*) — build where paired runs exist
    for dom in ["p8", "p15", "r3x4", "r3x5"]:
        build_bpmx_ratio(dom)

    for dom in ["p8", "p15", "r3x4", "r3x5"]:
        build_board_grid(dom)
    # 8-puzzle solvable vs unsolvable combo (if data available)
    build_unsolv_vs_solv_p8()

if __name__ == "__main__":
    main()
