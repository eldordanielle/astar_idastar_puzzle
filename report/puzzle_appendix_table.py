#!/usr/bin/env python3
from pathlib import Path
import os, glob, math
import numpy as np
import pandas as pd

# Where your CSVs already live (the same ones used to build the plots)
BASE = Path("results")
OUTD = Path("report/tables"); OUTD.mkdir(parents=True, exist_ok=True)

# Boards and display labels
BOARDS = {
    "p8":   "P 8",
    "p15":  "P 15",
    "r3x4": "R 3×4",
    "r3x5": "R 3×5",
}

# Heuristic aliases on disk → short display labels
HEUR_ALIASES = {
    "manhattan": ["manhattan"],
    "linear":    ["linear", "linear_conflict"],
}
HEUR_DISPLAY = {"manhattan": "Man", "linear": "LC"}

EVEN_DEPTHS = list(range(4, 22, 2))
EXCLUDE = ("bpmx", "unsolv", "unsolvable", "bfs", "dfs", "smoke", "sanity")

def geometric_mean(arr: np.ndarray) -> float:
    arr = np.asarray(arr, float)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    if arr.size == 0:
        return float("nan")
    return float(np.exp(np.mean(np.log(arr))))

def find_candidates(board: str, heur_key: str) -> list[Path]:
    pats = []
    for h in HEUR_ALIASES[heur_key]:
        pats += [
            str(BASE / f"{board}_{h}.csv"),
            str(BASE / f"{board}_{h}_*.csv"),
            str(BASE / f"{board}_*_{h}.csv"),
            str(BASE / f"{board}_*_{h}_*.csv"),
            # allow subfolders just in case
            str(BASE / f"**/{board}_{h}*.csv"),
            str(BASE / f"**/{board}_*_{h}*.csv"),
        ]
    out = []
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            name = os.path.basename(p).lower()
            if any(tag in name for tag in EXCLUDE):
                continue
            out.append(Path(p))
    # unique & stable
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
    need = {"algorithm", "depth", "time_sec"}
    if not need.issubset(df.columns):
        return None
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok") == "ok"]
    df = df[df["algorithm"].isin(["A*", "IDA*"])]
    return df if not df.empty else None

def collect_board_heur(board: str, heur_key: str) -> pd.DataFrame | None:
    files = find_candidates(board, heur_key)
    if not files: return None
    parts = []
    for p in files:
        d = load_ok(p)
        if d is not None: parts.append(d)
    if not parts: return None
    df = pd.concat(parts, ignore_index=True).drop_duplicates()
    # keep only the even-depth window
    df = df[df["depth"].isin(EVEN_DEPTHS)]
    if df.empty: return None
    # mean per algorithm, per depth (we aggregate repeats)
    g = (df.groupby(["algorithm", "depth"], as_index=False)
            .agg(time_sec=("time_sec", "mean")))
    return g

def main():
    rows = []
    for bcode, blabel in BOARDS.items():
        for hkey in ("manhattan", "linear"):
            g = collect_board_heur(bcode, hkey)
            if g is None:  # no data
                rows.append({
                    "Board": blabel, "Heur": HEUR_DISPLAY[hkey],
                    "Depths used": "", "n_depths": 0,
                    "Geo-mean IDA*/A* time": float("nan"),
                    "Win-fraction IDA*": float("nan"),
                    "First crossing depth (≥1)": ""
                })
                continue
            a = g[g["algorithm"] == "A*"].set_index("depth")["time_sec"]
            i = g[g["algorithm"] == "IDA*"].set_index("depth")["time_sec"]
            common = sorted(set(a.index).intersection(i.index).intersection(EVEN_DEPTHS))
            if not common:
                rows.append({
                    "Board": blabel, "Heur": HEUR_DISPLAY[hkey],
                    "Depths used": "", "n_depths": 0,
                    "Geo-mean IDA*/A* time": float("nan"),
                    "Win-fraction IDA*": float("nan"),
                    "First crossing depth (≥1)": ""
                })
                continue
            r = (i.loc[common] / a.loc[common]).values
            geo = geometric_mean(r)
            winfrac = float(np.mean(r < 1.0))
            # first crossing at or above parity, if any
            first_cross = ""
            for d, rv in zip(common, r):
                if rv >= 1.0:
                    first_cross = d
                    break
            rows.append({
                "Board": blabel,
                "Heur": HEUR_DISPLAY[hkey],
                "Depths used": " ".join(str(d) for d in common),
                "n_depths": len(common),
                "Geo-mean IDA*/A* time": geo,
                "Win-fraction IDA*": winfrac,
                "First crossing depth (≥1)": first_cross,
            })

    out = pd.DataFrame(rows)
    # tidy & round for display
    out["Geo-mean IDA*/A* time"] = out["Geo-mean IDA*/A* time"].round(3)
    out["Win-fraction IDA*"] = out["Win-fraction IDA*"].round(3)

    csv_path = OUTD / "cross_puzzle_summary.csv"
    xls_path = OUTD / "cross_puzzle_summary.xlsx"
    out.to_csv(csv_path, index=False)

    with pd.ExcelWriter(xls_path, engine="xlsxwriter") as xw:
        out.to_excel(xw, sheet_name="summary", index=False)

    print("✅ wrote:", csv_path)
    print("✅ wrote:", xls_path)

if __name__ == "__main__":
    main()
