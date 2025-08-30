#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

RES = Path("results")
RES.mkdir(exist_ok=True)

# canonical outputs per board/heuristic for §4.1 & §4.2
CANON = [
    ("p8",   "manhattan"),
    ("p8",   "linear_conflict"),
    ("p15",  "manhattan"),
    ("p15",  "linear_conflict"),
    ("r3x4", "manhattan"),
    ("r3x4", "linear_conflict"),
    ("r3x5", "manhattan"),
    ("r3x5", "linear_conflict"),
]

def load_ok(p: Path) -> pd.DataFrame | None:
    if not p.exists(): return None
    df = pd.read_csv(p)
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok") == "ok"]
    return df

for name, heur in CANON:
    parts = {
        "A*":    load_ok(RES / f"{name}_{heur}_a.csv"),
        "IDA*":  load_ok(RES / f"{name}_ida_{heur}_plain.csv"),
    }
    # Concatenate A* + IDA* (for per-depth curves & crossover)
    frames = []
    for algo, df in parts.items():
        if df is None: continue
        if "algorithm" not in df.columns:
            df["algorithm"] = algo
        else:
            df.loc[:, "algorithm"] = algo
        frames.append(df)
    if not frames:
        print(f"skip: {name}_{heur}.csv (missing inputs)"); continue
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RES / f"{name}_{heur}.csv", index=False)
    print(f"merged -> results/{name}_{heur}.csv")

print("✅ Canonical CSVs ready for figures.")
