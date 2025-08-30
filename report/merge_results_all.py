# report/merge_results_all.py
import os, glob, pandas as pd

OUTDIR = "results/merged"
os.makedirs(OUTDIR, exist_ok=True)

def merge_board(board_key: str):
    # collect everything relevant for this board from both folders
    pats = [
        f"results/*{board_key}*.csv",
        f"results/raw/*{board_key}*.csv",
    ]
    files = []
    for p in pats:
        files.extend(glob.glob(p))
    files = sorted(set(files))
    if not files:
        print(f"skip {board_key}: no sources found")
        return

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"warn: failed to read {f}: {e}")
            continue
        # normalize a few schema variants
        if "algo" in df.columns and "algorithm" not in df.columns:
            df = df.rename(columns={"algo": "algorithm"})
        if "time" in df.columns and "time_sec" not in df.columns:
            df = df.rename(columns={"time": "time_sec"})
        frames.append(df)

    if not frames:
        print(f"skip {board_key}: readable sources empty")
        return

    merged = pd.concat(frames, ignore_index=True)
    out = os.path.join(OUTDIR, f"{board_key}.csv")
    merged.to_csv(out, index=False)
    print(f"merged {board_key}: {len(merged):,} rows -> {out}")

for key in ["p8", "p15", "r3x4", "r3x5"]:
    merge_board(key)
