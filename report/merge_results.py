#!/usr/bin/env python3
import glob, os
from pathlib import Path
import pandas as pd

PAIRS = [
    ("p8","manhattan"),
    ("p8","linear_conflict"),
    ("p15","manhattan"),
    ("p15","linear_conflict"),
    ("r3x4","manhattan"),
    ("r3x4","linear_conflict"),
    ("r3x5","manhattan"),
    ("r3x5","linear_conflict"),
]

def load_many(patterns):
    dfs=[]
    for pat in patterns:
        for fn in glob.glob(pat):
            try:
                df = pd.read_csv(fn)
                df["__src__"] = os.path.basename(fn)
                dfs.append(df)
            except Exception as e:
                print(f"skip {fn}: {e}")
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True, sort=False)

    # Normalize schema
    if "algorithm" not in df.columns and "algo" in df.columns:
        df = df.rename(columns={"algo":"algorithm"})
    if "time_sec" not in df.columns and "time" in df.columns:
        df = df.rename(columns={"time":"time_sec"})

    # Keep clean rows only
    term = df.get("termination", "ok")
    df = df[term.fillna("ok") == "ok"]

    # Enforce types where possible
    for c in ("depth","seed","expanded","generated","duplicates"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "time_sec" in df.columns:
        df["time_sec"] = pd.to_numeric(df["time_sec"], errors="coerce")

    # Dedupe by algo+heuristic+depth+seed
    keep_cols = [c for c in ("algorithm","heuristic","depth","seed") if c in df.columns]
    if keep_cols:
        df = df.sort_values(keep_cols + (["time_sec"] if "time_sec" in df.columns else []))
        df = df.drop_duplicates(subset=keep_cols, keep="last")

    return df

def main():
    outdir = Path("results")
    outdir.mkdir(exist_ok=True)

    for dom, heur in PAIRS:
        pats = [
            f"results/{dom}_{heur}*.csv",                        # canonical
            f"results/{dom}_{heur.split('_')[0]}*.csv",          # loose matches
            f"results/{dom}_{heur}_astar_even_4_20.csv",         # new files
        ]
        df = load_many(pats)
        if df.empty:
            print(f"skip: {dom}_{heur} (no sources found)")
            continue

        df["heuristic"] = heur  # canonical label
        out = outdir / f"{dom}_{heur}.csv"
        df.to_csv(out, index=False)
        print(f"merged -> {out} ({len(df)} rows)")

if __name__ == "__main__":
    main()
