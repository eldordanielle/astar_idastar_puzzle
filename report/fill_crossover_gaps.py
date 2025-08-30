#!/usr/bin/env python3
"""
Fill missing depths (4..20 even) for A* and IDA* on all boards and both heuristics,
with a long timeout, then re-merge. Designed for the section 4.2 crossover plots.
"""
import os, sys, glob, subprocess, pandas as pd
from pathlib import Path

TARGET_DEPTHS = list(range(4, 21, 2))
HEURS = ["manhattan", "linear_conflict"]
BOARDS = [
    ("p8",   ["--domain","p8"],            "P 8"),
    ("p15",  ["--domain","p15"],           "P 15"),
    ("r3x4", ["--rows","3","--cols","4"],  "R 3×4"),
    ("r3x5", ["--rows","3","--cols","5"],  "R 3×5"),
]

MERGED_DIR = Path("results/merged")
RAW_DIR    = Path("results/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def _read_all_for_board(board_key: str) -> pd.DataFrame:
    """Read every CSV for a board from results/ and results/raw/, normalizing schemas."""
    paths = sorted(set(
        glob.glob(f"results/*{board_key}*.csv") +
        glob.glob(f"results/raw/*{board_key}*.csv")
    ))
    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        # normalize schema variants
        if "algo" in df.columns and "algorithm" not in df.columns:
            df = df.rename(columns={"algo":"algorithm"})
        if "time" in df.columns and "time_sec" not in df.columns:
            df = df.rename(columns={"time":"time_sec"})
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _ok_depths(df: pd.DataFrame, algo_substr: str, heur: str) -> set[int]:
    """Depths where we have termination==ok for this algo & heuristic."""
    if df.empty: return set()
    sel = df[
        df["heuristic"].eq(heur) &
        df["termination"].eq("ok") &
        df["algorithm"].astype(str).str.contains(algo_substr, regex=False)
    ]
    return set(int(x) for x in sel["depth"].dropna().unique().tolist())

def _run_runner(board_args, heur, depths_to_run, out_path,
                per_depth=30, timeout_sec=120.0):
    if not depths_to_run: return
    cmd = [
        sys.executable, "-m", "src.experiments.runner",
        "--algo","both",                      # generate A* and IDA*
        "--heuristic", heur,
        "--per_depth", str(per_depth),
        "--timeout_sec", str(timeout_sec),
        "--out", str(out_path),
        *board_args,
        "--depths", *[str(d) for d in depths_to_run],
    ]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    # 1) determine missing depths per (board, heuristic)
    to_fill = []  # list of (board_key, board_args, heur, missing_depths)
    for key, bargs, pretty in BOARDS:
        df = _read_all_for_board(key)
        for heur in HEURS:
            have_a   = _ok_depths(df, "A*",   heur)
            have_ida = _ok_depths(df, "IDA*", heur)
            missing  = [d for d in TARGET_DEPTHS if (d not in have_a) or (d not in have_ida)]
            print(f"{pretty:5s}/{heur:15s}  haveA={sorted(have_a)}  haveIDA={sorted(have_ida)}  missing={missing}")
            if missing:
                to_fill.append((key, bargs, heur, missing))

    # 2) run fills (A*+IDA* together) with longer timeout
    for key, bargs, heur, missing in to_fill:
        out_name = f"fill_{key}_{heur}_{min(missing)}_{max(missing)}.csv"
        _run_runner(bargs, heur, missing, RAW_DIR/out_name, per_depth=30, timeout_sec=120.0)

    # 3) re-merge into results/merged/{p8,p15,r3x4,r3x5}.csv
    # (inline merge so you don’t have to run a separate script)
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    for key, _, _ in BOARDS:
        df = _read_all_for_board(key)
        if df.empty:
            print(f"skip merge {key}: no rows")
            continue
        out = MERGED_DIR / f"{key}.csv"
        df.to_csv(out, index=False)
        print(f"merged {key}: {len(df):,} rows -> {out}")

    print("\nDone. Re-run your plotting script for 4.2 (ratio grid & common).")

if __name__ == "__main__":
    main()
