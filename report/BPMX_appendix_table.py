#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, numpy as np, glob, os, re

# ---------- Config ----------
BASE = Path("results")
OUTD = Path("report/tables"); OUTD.mkdir(parents=True, exist_ok=True)
XLS = OUTD / "bpmx_appendix.xlsx"

BOARDS = {"p8":"P 8", "p15":"P 15", "r3x4":"R 3×4", "r3x5":"R 3×5"}
HEUR_ALIASES = {"manhattan":["manhattan"], "linear":["linear","linear_conflict"]}
HEUR_DISPLAY = {"manhattan":"Man", "linear":"LC"}
EVEN_DEPTHS = list(range(4, 21, 2))

# NOTE: unlike other scripts, we DO NOT exclude 'bpmx' files here (we need them).
EXCLUDE = re.compile(r"(unsolv|unsolvable|bfs|dfs|smoke|sanity|astar_vs_ida)", re.I)

IDA_LABEL      = "IDA*"
IDA_BPMX_LABEL = "IDA* (BPMX ON)"

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1)/np.sqrt(n)

def find_candidates(board: str, heur_key: str) -> list[Path]:
    """
    Find CSVs for this board; we'll filter by heuristic AFTER loading
    to avoid filename mismatches.
    """
    pats = [
        f"{board}_*.csv", f"{board}*.csv",
        f"**/{board}_*.csv", f"**/{board}*.csv",
    ]
    out = []
    for pat in pats:
        for p in glob.glob(str(BASE / pat), recursive=True):
            name = os.path.basename(p).lower()
            if EXCLUDE.search(name):  # exclude noise, keep bpmx
                continue
            out.append(Path(p))
    # unique, sorted
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
    need_any = {"algorithm","depth","time_sec"}
    if not need_any.issubset(df.columns):
        return None
    # Only OK terminations
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok")=="ok"].copy()
    # Only solvable when column present
    if "solvable" in df.columns:
        df = df[df["solvable"]==1].copy()
    # Ensure required numeric columns exist (filled with NaN if missing)
    for c in ("expanded","generated"):
        if c not in df.columns:
            df[c] = np.nan
    return df

def collect_pair(board: str, heur_key: str) -> pd.DataFrame | None:
    files = find_candidates(board, heur_key)
    if not files: return None
    dfs = []
    for p in files:
        d = load_ok(p)
        if d is None or d.empty: continue
        # Heuristic filter: accept any alias variant if heuristic column exists
        if "heuristic" in d.columns:
            aliases = HEUR_ALIASES[heur_key]
            d = d[d["heuristic"].isin(aliases)]
            if d.empty: continue
        # Keep only the two IDA variants
        d = d[d["algorithm"].isin([IDA_LABEL, IDA_BPMX_LABEL])]
        if d.empty: continue
        dfs.append(d)
    if not dfs: return None
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Restrict to even depths 4..20 if present
    df = df[df["depth"].isin(EVEN_DEPTHS)]
    if df.empty: return None

    # Aggregate per algorithm & depth
    g = (df.groupby(["algorithm","depth"], as_index=False)
           .agg(expanded_mean=("expanded","mean"),
                expanded_sem =("expanded", sem),
                generated_mean=("generated","mean"),
                generated_sem =("generated", sem),
                time_sec_mean=("time_sec","mean"),
                time_sec_sem =("time_sec", sem),
                n=("time_sec","count")))
    g.insert(0, "board", BOARDS[board])
    g.insert(1, "heuristic", HEUR_DISPLAY[heur_key])  # Man / LC
    return g.sort_values(["board","heuristic","algorithm","depth"]).reset_index(drop=True)

def ratio_sheet(block: pd.DataFrame) -> pd.DataFrame:
    # One row per common depth with BPMX/Plain ratios and delta %
    a = block[block["algorithm"]==IDA_LABEL     ].set_index("depth")
    b = block[block["algorithm"]==IDA_BPMX_LABEL].set_index("depth")
    common = sorted(set(a.index).intersection(b.index))
    rows = []
    for d in common:
        r_exp = b.loc[d,"expanded_mean"] / a.loc[d,"expanded_mean"] if a.loc[d,"expanded_mean"]>0 else np.nan
        r_gen = b.loc[d,"generated_mean"] / a.loc[d,"generated_mean"] if a.loc[d,"generated_mean"]>0 else np.nan
        r_tim = b.loc[d,"time_sec_mean"]  / a.loc[d,"time_sec_mean"]  if a.loc[d,"time_sec_mean"]>0  else np.nan
        # approximate SEM of a ratio (independent samples)
        with np.errstate(divide="ignore", invalid="ignore"):
            sem_exp = np.sqrt((b.loc[d,"expanded_sem"]/b.loc[d,"expanded_mean"])**2 +
                              (a.loc[d,"expanded_sem"]/a.loc[d,"expanded_mean"])**2) * r_exp if r_exp==r_exp else np.nan
            sem_gen = np.sqrt((b.loc[d,"generated_sem"]/b.loc[d,"generated_mean"])**2 +
                              (a.loc[d,"generated_sem"]/a.loc[d,"generated_mean"])**2) * r_gen if r_gen==r_gen else np.nan
            sem_tim = np.sqrt((b.loc[d,"time_sec_sem"]/b.loc[d,"time_sec_mean"])**2 +
                              (a.loc[d,"time_sec_sem"]/a.loc[d,"time_sec_mean"])**2) * r_tim if r_tim==r_tim else np.nan
        rows.append({
            "Board": block["board"].iloc[0],
            "Heur":  block["heuristic"].iloc[0],
            "Depth": d,
            "Ratio: BPMX/Plain (Expanded)": r_exp,
            "SEM (Expanded)": sem_exp,
            "Ratio: BPMX/Plain (Generated)": r_gen,
            "SEM (Generated)": sem_gen,
            "Ratio: BPMX/Plain (Time)": r_tim,
            "SEM (Time)": sem_tim,
            "n_plain": int(a.loc[d,"n"]) if "n" in a.columns else np.nan,
            "n_bpmx":  int(b.loc[d,"n"]) if "n" in b.columns else np.nan,
            "ΔTime % (BPMX vs Plain)": (r_tim-1.0)*100.0 if r_tim==r_tim else np.nan,
            "ΔGen % (BPMX vs Plain)":  (1.0-r_gen)*100.0 if r_gen==r_gen else np.nan
        })
    return pd.DataFrame(rows)

def coverage_rows(block: pd.DataFrame) -> pd.DataFrame:
    # Which even depths (4..20) appear for both algos?
    a = set(block[block["algorithm"]==IDA_LABEL]["depth"])
    b = set(block[block["algorithm"]==IDA_BPMX_LABEL]["depth"])
    common = sorted(a & b)
    missing = [d for d in EVEN_DEPTHS if d not in common]
    return pd.DataFrame([{
        "Board": block["board"].iloc[0],
        "Heur":  block["heuristic"].iloc[0],
        "Depths available (both)": ", ".join(map(str, common)) if common else "",
        "Missing depths (either side)": ", ".join(map(str, missing)) if missing else ""
    }])

def main():
    blocks = []
    for b in BOARDS:
        for h in ("manhattan","linear"):
            blk = collect_pair(b, h)
            if blk is not None and not blk.empty:
                blocks.append(blk)

    if not blocks:
        raise SystemExit("No BPMX/Plain IDA* data found under results/.")

    full = pd.concat(blocks, ignore_index=True)
    # Ordering + short labels
    full["algorithm"] = pd.Categorical(full["algorithm"], [IDA_LABEL, IDA_BPMX_LABEL], ordered=True)
    full["heuristic"] = pd.Categorical(full["heuristic"], ["Man","LC"], ordered=True)
    full["board"]     = pd.Categorical(full["board"], ["P 8","P 15","R 3×4","R 3×5"], ordered=True)
    full = full.sort_values(["board","heuristic","depth","algorithm"]).reset_index(drop=True)

    # Rounding: SEMs to 3 dp; keep means (exp/gen) to 1 dp; times to 6 dp (string)
    disp = full.copy()
    disp["expanded_mean"]  = disp["expanded_mean"].round(1)
    disp["expanded_sem"]   = disp["expanded_sem"].round(3)
    disp["generated_mean"] = disp["generated_mean"].round(1)
    disp["generated_sem"]  = disp["generated_sem"].round(3)
    # Format times for consistent display
    disp["time_sec_mean_str"] = disp["time_sec_mean"].map(lambda v: f"{float(v):.6f}")
    disp["time_sec_sem_str"]  = disp["time_sec_sem"].map(lambda v: f"{float(v):.6f}")

    # Build ratio + coverage sheets
    ratio_parts, cover_parts = [], []
    for (brd, heur), part in disp.groupby(["board","heuristic"], sort=False):
        r = ratio_sheet(part)
        c = coverage_rows(part)
        if not r.empty: ratio_parts.append(r)
        if not c.empty: cover_parts.append(c)

    ratios   = pd.concat(ratio_parts, ignore_index=True) if ratio_parts else pd.DataFrame()
    coverage = pd.concat(cover_parts, ignore_index=True) if cover_parts else pd.DataFrame()

    # Write Excel
    with pd.ExcelWriter(XLS, engine="xlsxwriter") as xw:
        # Long-form per-depth stats (short labels; times as numbers + strings)
        cols = ["board","heuristic","algorithm","depth",
                "expanded_mean","expanded_sem",
                "generated_mean","generated_sem",
                "time_sec_mean","time_sec_sem",
                "time_sec_mean_str","time_sec_sem_str","n"]
        disp[cols].rename(columns={
            "board":"Board","heuristic":"Heur","algorithm":"Alg.","depth":"d",
            "expanded_mean":"Exp (mean)","expanded_sem":"Exp (SEM)",
            "generated_mean":"Gen (mean)","generated_sem":"Gen (SEM)",
            "time_sec_mean":"Time (s, mean) [num]","time_sec_sem":"Time (s, SEM) [num]",
            "time_sec_mean_str":"Time (s, mean)","time_sec_sem_str":"Time (s, SEM)",
            "n":"n"
        }).to_excel(xw, sheet_name="per_depth_stats", index=False)

        if not ratios.empty:
            ratios.to_excel(xw, sheet_name="bpmx_over_plain_ratio", index=False)
        if not coverage.empty:
            coverage.to_excel(xw, sheet_name="coverage_4_20_even", index=False)

    print(f"✅ wrote: {XLS}")

if __name__ == "__main__":
    main()
