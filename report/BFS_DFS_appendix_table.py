#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, numpy as np, glob, os, re

# ---------- Config ----------
BASE = Path("results")
OUTD = Path("report/tables"); OUTD.mkdir(parents=True, exist_ok=True)
XLS = OUTD / "bfs_dfs_appendix.xlsx"

BOARDS = {"p8":"P 8", "p15":"P 15", "r3x4":"R 3×4", "r3x5":"R 3×5"}
EVEN_DEPTHS = list(range(4, 21, 2))  # for coverage reporting

# Include only BFS/DFS; exclude unrelated experiments/shards
EXCLUDE = re.compile(r"(unsolv|unsolvable|bpmx|ida|astar|a\*|smoke|sanity)", re.I)

def sem(x):
    x = np.asarray(x, float)
    n = np.sum(~np.isnan(x))
    return 0.0 if n <= 1 else np.nanstd(x, ddof=1) / np.sqrt(n)

def find_candidates(board: str) -> list[Path]:
    """
    Find CSVs for this board that look like BFS/DFS outputs.
    """
    pats = [
        f"{board}_*.csv", f"{board}*.csv",
        f"**/{board}_*.csv", f"**/{board}*.csv",
    ]
    out = []
    for pat in pats:
        for p in glob.glob(str(BASE / pat), recursive=True):
            name = os.path.basename(p).lower()
            if EXCLUDE.search(name):
                continue
            # keep only files whose name hints BFS/DFS
            if ("bfs" not in name) and ("dfs" not in name):
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
    need = {"algorithm","depth","time_sec"}
    if not need.issubset(df.columns):
        return None

    # Only successful finishes
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok") == "ok"].copy()
    # Only solvable when column present
    if "solvable" in df.columns:
        df = df[df["solvable"] == 1].copy()

    # Keep BFS/DFS rows only
    df = df[df["algorithm"].isin(["BFS","DFS"])].copy()
    if df.empty:
        return None

    # Fill missing metrics so aggregation doesn't break
    for c in ("expanded","generated"):
        if c not in df.columns:
            df[c] = np.nan
    return df

def collect_board(board: str) -> pd.DataFrame | None:
    files = find_candidates(board)
    if not files: return None
    dfs = []
    for p in files:
        d = load_ok(p)
        if d is not None and not d.empty:
            dfs.append(d)
    if not dfs: return None
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()

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
    return g.sort_values(["board","algorithm","depth"]).reset_index(drop=True)

def ratio_sheet(block: pd.DataFrame) -> pd.DataFrame:
    """
    DFS/BFS ratios on common depths.
    """
    b = block[block["algorithm"]=="BFS"].set_index("depth")
    d = block[block["algorithm"]=="DFS"].set_index("depth")
    common = sorted(set(b.index) & set(d.index))
    rows = []
    for x in common:
        # Ratios (DFS/BFS)
        def _ratio(num, den): return (num / den) if (den and den>0) else np.nan
        r_exp = _ratio(d.loc[x,"expanded_mean"], b.loc[x,"expanded_mean"])
        r_gen = _ratio(d.loc[x,"generated_mean"], b.loc[x,"generated_mean"])
        r_tim = _ratio(d.loc[x,"time_sec_mean"],  b.loc[x,"time_sec_mean"])
        # SEM of ratio (approx., independent)
        with np.errstate(divide="ignore", invalid="ignore"):
            sem_exp = np.sqrt((d.loc[x,"expanded_sem"]/d.loc[x,"expanded_mean"])**2 +
                              (b.loc[x,"expanded_sem"]/b.loc[x,"expanded_mean"])**2) * r_exp if r_exp==r_exp else np.nan
            sem_gen = np.sqrt((d.loc[x,"generated_sem"]/d.loc[x,"generated_mean"])**2 +
                              (b.loc[x,"generated_sem"]/b.loc[x,"generated_mean"])**2) * r_gen if r_gen==r_gen else np.nan
            sem_tim = np.sqrt((d.loc[x,"time_sec_sem"]/d.loc[x,"time_sec_mean"])**2 +
                              (b.loc[x,"time_sec_sem"]/b.loc[x,"time_sec_mean"])**2) * r_tim if r_tim==r_tim else np.nan
        rows.append({
            "Board": block["board"].iloc[0],
            "Depth": x,
            "DFS/BFS (Expanded)": r_exp, "SEM (Expanded)": sem_exp,
            "DFS/BFS (Generated)": r_gen, "SEM (Generated)": sem_gen,
            "DFS/BFS (Time)":      r_tim, "SEM (Time)":      sem_tim,
            "n_BFS": int(b.loc[x,"n"]) if "n" in b.columns else np.nan,
            "n_DFS": int(d.loc[x,"n"]) if "n" in d.columns else np.nan,
            "ΔTime % (DFS vs BFS)": (r_tim-1.0)*100.0 if r_tim==r_tim else np.nan
        })
    return pd.DataFrame(rows)

def coverage_rows(block: pd.DataFrame) -> pd.DataFrame:
    """
    Which even depths 4..20 exist for BFS and DFS?
    """
    b = set(block[block["algorithm"]=="BFS"]["depth"])
    d = set(block[block["algorithm"]=="DFS"]["depth"])
    both = sorted(b & d)
    miss_b = [x for x in EVEN_DEPTHS if x not in b]
    miss_d = [x for x in EVEN_DEPTHS if x not in d]
    return pd.DataFrame([{
        "Board": block["board"].iloc[0],
        "BFS depths": ", ".join(map(str, sorted(b))) if b else "",
        "DFS depths": ", ".join(map(str, sorted(d))) if d else "",
        "Common depths (even 4–20)": ", ".join(map(str, both)) if both else "",
        "Missing BFS (even 4–20)": ", ".join(map(str, miss_b)) if miss_b else "",
        "Missing DFS (even 4–20)": ", ".join(map(str, miss_d)) if miss_d else "",
    }])

def main():
    blocks = []
    for b in BOARDS:
        blk = collect_board(b)
        if blk is not None and not blk.empty:
            blocks.append(blk)

    if not blocks:
        raise SystemExit("No BFS/DFS data found under results/.")

    full = pd.concat(blocks, ignore_index=True)
    full["algorithm"] = pd.Categorical(full["algorithm"], ["BFS","DFS"], ordered=True)
    full["board"]     = pd.Categorical(full["board"], ["P 8","P 15","R 3×4","R 3×5"], ordered=True)
    full = full.sort_values(["board","algorithm","depth"]).reset_index(drop=True)

    # Display copy with rounding:
    disp = full.copy()
    disp["expanded_mean"]  = disp["expanded_mean"].round(1)
    disp["expanded_sem"]   = disp["expanded_sem"].round(3)
    disp["generated_mean"] = disp["generated_mean"].round(1)
    disp["generated_sem"]  = disp["generated_sem"].round(3)
    disp["time_sec_mean_str"] = disp["time_sec_mean"].map(lambda v: f"{float(v):.6f}")
    disp["time_sec_sem_str"]  = disp["time_sec_sem"].map(lambda v: f"{float(v):.6f}")

    # Build ratio + coverage sheets
    ratio_parts, cover_parts = [], []
    for brd, part in disp.groupby("board", sort=False):
        r = ratio_sheet(part)
        c = coverage_rows(part)
        if not r.empty: ratio_parts.append(r)
        if not c.empty: cover_parts.append(c)

    ratios   = pd.concat(ratio_parts, ignore_index=True) if ratio_parts else pd.DataFrame()
    coverage = pd.concat(cover_parts, ignore_index=True) if cover_parts else pd.DataFrame()

    # Write Excel
    with pd.ExcelWriter(XLS, engine="xlsxwriter") as xw:
        disp.rename(columns={
            "board":"Board","algorithm":"Alg.","depth":"d",
            "expanded_mean":"Exp (mean)","expanded_sem":"Exp (SEM)",
            "generated_mean":"Gen (mean)","generated_sem":"Gen (SEM)",
            "time_sec_mean":"Time (s, mean) [num]","time_sec_sem":"Time (s, SEM) [num]",
            "time_sec_mean_str":"Time (s, mean)","time_sec_sem_str":"Time (s, SEM)",
            "n":"n"
        })[["Board","Alg.","d",
            "Exp (mean)","Exp (SEM)","Gen (mean)","Gen (SEM)",
            "Time (s, mean) [num]","Time (s, SEM) [num]",
            "Time (s, mean)","Time (s, SEM)","n"]].to_excel(
                xw, sheet_name="per_depth_stats", index=False)

        if not ratios.empty:
            ratios.to_excel(xw, sheet_name="dfs_over_bfs_ratio", index=False)
        if not coverage.empty:
            coverage.to_excel(xw, sheet_name="coverage_4_20_even", index=False)

    print(f"✅ wrote: {XLS}")

if __name__ == "__main__":
    main()
