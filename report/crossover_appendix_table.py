#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import numpy as np
import glob
import re

BASE = Path("results")
OUTD = Path("report/tables")
OUTD.mkdir(parents=True, exist_ok=True)

# Boards → display labels
BOARDS = {"p8":"P 8", "p15":"P 15", "r3x4":"R 3×4", "r3x5":"R 3×5"}

# Heuristic aliases on disk; display labels are now short: "Man" / "LC"
HEUR_ALIASES = {"manhattan":["manhattan"], "linear":["linear","linear_conflict"]}
HEUR_DISPLAY = {"manhattan":"Man", "linear":"LC"}

# Exclude special-purpose files
EXCLUDE = re.compile(r"(bpmx|unsolv|unsolvable|solv|astar_vs_ida|smoke|sanity)", re.I)

DEPTH_MIN, DEPTH_MAX = 4, 20

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def find_candidates(board: str, heur_key: str) -> list[Path]:
    pats = []
    for h in HEUR_ALIASES[heur_key]:
        pats += [
            str(BASE / f"{board}_{h}.csv"),
            str(BASE / f"{board}_{h}_*.csv"),
            str(BASE / f"{board}_*_{h}.csv"),
            str(BASE / f"{board}_*_{h}_*.csv"),
        ]
    cands = []
    for pat in pats:
        for p in glob.glob(pat):
            p = Path(p)
            if p.exists() and not EXCLUDE.search(p.name):
                cands.append(p)
    seen, out = set(), []
    for p in sorted(cands):
        if p not in seen:
            seen.add(p); out.append(p)
    return out

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
    for c in ("expanded","generated"):
        if c not in df.columns:
            df[c] = np.nan
    return df

def collect_block(board: str, heur_key: str) -> pd.DataFrame | None:
    files = find_candidates(board, heur_key)
    if not files: return None
    dfs = []
    for p in files:
        d = load_ok(p)
        if d is not None and not d.empty:
            dfs.append(d)
    if not dfs: return None
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    df = df[(df["depth"] >= DEPTH_MIN) & (df["depth"] <= DEPTH_MAX)]
    if df.empty: return None
    g = (df.groupby(["algorithm","depth"], as_index=False)
           .agg(expanded_mean=("expanded","mean"),
                expanded_sem =("expanded", sem),
                generated_mean=("generated","mean"),
                generated_sem =("generated", sem),
                time_sec_mean=("time_sec","mean"),
                time_sec_sem =("time_sec", sem),
                n=("time_sec","count")))
    g.insert(0, "board", BOARDS[board])
    g.insert(1, "heuristic", HEUR_DISPLAY[heur_key])  # "Man" or "LC"
    return g

def build_summary():
    blocks = []
    for b in BOARDS:
        for h in ("manhattan","linear"):
            blk = collect_block(b, h)
            if blk is not None:
                blocks.append(blk)
    if not blocks:
        raise SystemExit("No data found to build the appendix table.")

    summary = pd.concat(blocks, ignore_index=True)

    # ordering
    summary["algorithm"] = pd.Categorical(summary["algorithm"], ["A*","IDA*"], ordered=True)
    summary["heuristic"] = pd.Categorical(summary["heuristic"], ["Man","LC"], ordered=True)
    summary["board"] = pd.Categorical(summary["board"], ["P 8","P 15","R 3×4","R 3×5"], ordered=True)
    summary = summary.sort_values(["board","heuristic","depth","algorithm"]).reset_index(drop=True)

    # ======= DISPLAY-FRIENDLY VERSIONS (short labels, rounding) =======
    # copy for CSV/Excel/LaTeX so the pasted table is narrower in Word
    disp = summary.copy()

    # rounding rules
    # - expanded_mean, generated_mean: 1 dp (unchanged)
    # - expanded_sem: ***3 dp*** (as requested)
    # - generated_sem: 3 dp as well (keeps columns aligned; optional)
    # - time_sec_*: keep 6 dp (timing precision)
    disp["expanded_mean"]  = disp["expanded_mean"].round(1)
    disp["expanded_sem"]   = disp["expanded_sem"].round(3)   # <-- your request
    disp["generated_mean"] = disp["generated_mean"].round(1)
    disp["generated_sem"]  = disp["generated_sem"].round(3)  # keep consistent
    # leave time_sec_mean/sem as floats; Excel/Word will show them compactly

    # Write CSV / Excel
    csv_path = OUTD / "per_depth_summary.csv"
    xls_path = OUTD / "per_depth_summary.xlsx"
    disp.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xls_path, engine="xlsxwriter") as xw:
        disp.to_excel(xw, sheet_name="summary", index=False)

        # ratio sheet (IDA*/A* time), with short heuristic labels
        rows = []
        for (brd, heur), part in disp.groupby(["board","heuristic"]):
            a = part[part["algorithm"]=="A*"].set_index("depth")
            i = part[part["algorithm"]=="IDA*"].set_index("depth")
            common = sorted(set(a.index).intersection(i.index))
            if not common: continue
            ta, ti = a.loc[common,"time_sec_mean"].values, i.loc[common,"time_sec_mean"].values
            sa, si = a.loc[common,"time_sec_sem"].values,  i.loc[common,"time_sec_sem"].values
            r = ti/ta
            with np.errstate(divide="ignore", invalid="ignore"):
                rsem = np.sqrt((si/ti)**2 + (sa/ta)**2) * r
            rows.append(pd.DataFrame({
                "Board": brd, "Heur": heur, "Depth": common,
                "IDA*/A* time (mean)": r, "IDA*/A* time (SEM)": rsem
            }))
        if rows:
            ratios = pd.concat(rows, ignore_index=True)
            ratios.to_excel(xw, sheet_name="ida_over_astar_ratio", index=False)

    # LaTeX longtable (short labels + rounding)
    s2 = disp.rename(columns={
        "board":"Board","heuristic":"Heur","algorithm":"Alg.","depth":"d",
        "expanded_mean":"Exp (mean)","expanded_sem":"Exp (SEM)",
        "generated_mean":"Gen (mean)","generated_sem":"Gen (SEM)",
        "time_sec_mean":"Time (s, mean)","time_sec_sem":"Time (s, SEM)","n":"n"
    }).copy()

    # Format times to fixed 6 dp for consistency in PDF
    for c in ["Time (s, mean)","Time (s, SEM)"]:
        s2[c] = s2[c].map(lambda v: f"{v:.6f}")

    tex_path = OUTD / "per_depth_summary.tex"
    latex = s2.to_latex(index=False, longtable=True, escape=False,
                        caption=("Per-depth results (d=6–20) for A* and IDA* across "
                                 "P 8, P 15, R 3×4, R 3×5 under Man (Manhattan) and LC (Linear Conflict). "
                                 "Means ± SEM; rows filtered to termination=ok."),
                        label="tab:per-depth-summary")
    Path(tex_path).write_text(latex)

    print("✅ wrote:", csv_path)
    print("✅ wrote:", xls_path)
    print("✅ wrote:", tex_path)

if __name__ == "__main__":
    build_summary()
