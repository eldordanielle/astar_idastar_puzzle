#!/bin/bash
#SBATCH --job-name=s-unsolv-array
#SBATCH --time=0-06:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=logs/s-unsolv-%A_%a.out
#SBATCH --array=0-35   # 4 boards × 9 depths (4..20 step2) = 36 tasks

set -euo pipefail
module purge 2>/dev/null || true

cd "$SLURM_SUBMIT_DIR"

# Map array index -> board,depth
boards=(p8 p15 r3x4 r3x5)
depths=(4 6 8 10 12 14 16 18 20)

b_idx=$(( SLURM_ARRAY_TASK_ID / ${#depths[@]} ))
d_idx=$(( SLURM_ARRAY_TASK_ID % ${#depths[@]} ))

board=${boards[$b_idx]}
depth=${depths[$d_idx]}

# Per-depth repeats and timeout (tune to your cluster)
PER=8
TMO=20

# Set domain flags
dom_flags=()
case "$board" in
  p8)  dom_flags+=(--domain p8) ;;
  p15) dom_flags+=(--domain p15) ;;
  r3x4) dom_flags+=(--rows 3 --cols 4) ;;
  r3x5) dom_flags+=(--rows 3 --cols 5) ;;
esac

out="results/${board}_unsolv_ida_d${depth}.csv"
mkdir -p results logs

# Only IDA* (faster memory-wise), unsolvable only via --include_unsolvable
python -m src.experiments.runner "${dom_flags[@]}" --algo ida \
  --heuristic manhattan --depths $depth --per_depth $PER \
  --timeout_sec $TMO --include_unsolvable --out "$out"
