#!/bin/bash
#SBATCH --time 0-08:00:00
#SBATCH --job-name unsolv_all
#SBATCH --output job-unsolv-all-%J.out
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
# Optional email:
# #SBATCH --mail-type=END,FAIL
# #SBATCH --mail-user=eldord@post.bgu.ac.il

# === EDIT ME: repo location ===
PROJECT_DIR="/home/eldord/astar_idastar_puzzle"

cd "$PROJECT_DIR" || exit 1

# Optional conda env (uncomment if you use it)
# source ~/.bashrc
# conda activate astar

# Boards and depths
DEPTHS=(4 6 8 10 12 14 16 18 20)

run_both_domain() {
  local board="$1"
  local outprefix="$2"
  local args=("${@:3}")  # domain args
  for d in "${DEPTHS[@]}"; do
    OUT="results/${outprefix}_unsolv_manhattan_d${d}.csv"
    if [ ! -s "$OUT" ]; then
      echo "[RUN] ${outprefix} depth=$d -> $OUT"
      python -m src.experiments.runner "${args[@]}" \
        --algo both --heuristic manhattan --depths "$d" --per_depth 12 \
        --include_unsolvable --timeout_sec 30 --out "$OUT"
    else
      echo "[SKIP] $OUT exists"
    fi
  done
}

# Squares
run_both_domain p8  p8   --domain p8
run_both_domain p15 p15  --domain p15

# Rectangles
run_both_domain r3x4 r3x4 --rows 3 --cols 4
run_both_domain r3x5 r3x5 --rows 3 --cols 5

# Merge per-board shards
python - <<'PY'
import glob, pandas as pd, os
boards = ["p8","p15","r3x4","r3x5"]
for b in boards:
    files = sorted(glob.glob(f"results/{b}_unsolv_manhattan_d*.csv"))
    if not files:
        print(f"[merge] skip {b}: no shards found")
        continue
    df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True).drop_duplicates()
    out = f"results/{b}_unsolv_manhattan.csv"
    df.to_csv(out, index=False)
    print(f"[merge] wrote {out} from {len(files)} shards, rows={len(df)}")
PY

echo "DONE: unsolvable/solvable A* & IDA* for all boards."
