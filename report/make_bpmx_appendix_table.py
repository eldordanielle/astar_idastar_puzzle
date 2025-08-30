#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import numpy as np
import math

RES = Path("results"); OUT = Path("report/figs"); OUT.mkdir(parents=True, exist_ok=True)
BOARDS = [("p8","P 8"), ("p15","P 15"), ("r3x4","R 3×4"), ("r3x5","R 3×5")]
HEURS  = [("manhattan","Man"), ("linear_conflict","LC")]

def load_ok(p: Path) -> pd.DataFrame | None:
    if not p.exists(): return None
    df = pd.read_csv(p)
    if "termination" in df.columns:
        df = df[df["termination"].fillna("ok")=="ok"]
    return df

def sem(a):
    a = a.dropna().to_numpy()
    n = len(a)
    if n <= 1: return 0.0
    return float(np.std(a, ddof=1) / math.sqrt(n))

rows = []
for b,b_label in BOARDS:
    for h,h_label in HEURS:
        # expect separate plain/bpmx files
        p_plain = RES / f"{b}_ida_{h}_plain.csv"
        p_bpmx  = RES / f"{b}_ida_{h}_bpmx.csv"
        dfP, dfB = load_ok(p_plain), load_ok(p_bpmx)
        if dfP is None or dfB is None:
            print("skip:", b, h, "(missing files)"); continue
        for d in range(4, 21, 2):
            DP = dfP[dfP["depth"]==d]
            DB = dfB[dfB["depth"]==d]
            if DP.empty or DB.empty: continue
            for tag, DF in [("Plain", DP), ("BPMX", DB)]:
                rows.append({
                    "board": b_label, "heur": h_label, "depth": d, "variant": tag,
                    "expanded_mean":  DF["expanded"].mean(),
                    "expanded_sem":   sem(DF["expanded"]),
                    "generated_mean": DF["generated"].mean(),
                    "generated_sem":  sem(DF["generated"]),
                    "time_mean":      DF["time_sec"].mean(),
                    "time_sem":       sem(DF["time_sec"]),
                    "n":              len(DF)
                })

table = pd.DataFrame(rows)
# compact formatting for Word: abbreviate headers, 3 decimals on SEM, 3–4 sig figs on means
def fmt3(x): 
    return "" if pd.isna(x) else f"{x:.3f}"
def fmtm(x):
    return "" if pd.isna(x) else f"{x:.4g}"

table_sorted = (table
    .sort_values(["board","heur","depth","variant"])
    .assign(expanded_sem=lambda df: df["expanded_sem"].map(fmt3),
            generated_sem=lambda df: df["generated_sem"].map(fmt3),
            time_sem=lambda df: df["time_sem"].map(fmt3),
            expanded_mean=lambda df: df["expanded_mean"].map(fmtm),
            generated_mean=lambda df: df["generated_mean"].map(fmtm),
            time_mean=lambda df: df["time_mean"].map(fmtm))
)

csv_out = RES / "appendix_bpmx_values.csv"
md_out  = RES / "appendix_bpmx_values.md"
table_sorted.to_csv(csv_out, index=False)

# Markdown (narrow headers)
cols = ["board","heur","depth","variant",
        "expanded_mean","expanded_sem",
        "generated_mean","generated_sem",
        "time_mean","time_sem","n"]
with open(md_out, "w") as f:
    f.write("| " + " | ".join(cols) + " |\n")
    f.write("|" + "|".join(["---"]*len(cols)) + "|\n")
    for _,r in table_sorted[cols].iterrows():
        f.write("| " + " | ".join(str(r[c]) for c in cols) + " |\n")

print("✅ Saved:", csv_out)
print("✅ Saved:", md_out)
