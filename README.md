# 🧩 A* vs. IDA* on Sliding‑Tile Puzzles (8, 15, 3×4, 3×5)

End‑to‑end, reproducible experiments comparing **A\*** and **IDA\*** on classic sliding‑tile puzzles under **Manhattan** and **Linear Conflict (LC)** heuristics, with **BPMX**, **BFS/DFS** baselines, **solvable vs. unsolvable** analysis, and an **A\* tie‑breaking ablation**.  
All figures and appendix tables are generated from CSVs produced by a single runner.

---

## 🔎 What’s inside

- **A\* vs. IDA\***: time, expansions, duplicate rate, and memory proxies across depths **4…20**.  
- **BPMX on IDA\***: ratio plots (BPMX / Plain).  
- **BFS vs. DFS**: bookend baselines for uninformed search.  
- **Solvable vs. Unsolvable**: cost to prove vs. disprove reachability.  
- **A\* tie‑breaking (h/g/fifo/lifo)**: robustness check.  
- Cross‑puzzle summary bars + appendix tables (CSV/XLSX).

**Headline:** IDA\* dominates at shallow–moderate depths; A\* catches up when `CLOSED` fits (especially with LC). BPMX didn’t help in this Python setting. Unsolvables are a mid‑depth constant‑factor tax (often ≤2×), not a different growth rate. A\* is robust to tie‑breaking.

---

## 📁 Layout

```
src/
  experiments/runner.py        # single entry point for all runs
  search/                      # A*, IDA*, BPMX, BFS, DFS
report/
  figs/                        # generated figures (PNG)
  tables/                      # appendix tables (CSV/XLSX)
  *.py                         # plotting/table scripts (self-contained)
results/                       # CSV outputs (created by the runner)
```

---

## ⚙️ Setup

```bash
git clone <YOUR-REPO-URL> astar_idastar_puzzle
cd astar_idastar_puzzle

# Optional: conda/venv
# conda create -n astar python=3.11 -y && conda activate astar

pip install -r requirements.txt
```

All scripts are non‑interactive; figures/tables are written to `report/figs` and `report/tables`.

---

## ▶️ Reproducing the data

The runner accepts either `--domain p8|p15` **or** `--rows 3 --cols 4/5`.  
Common knobs: `--algo a|ida|bfs|dfs|both`, `--heuristic manhattan|linear_conflict`, `--bpmx`, `--tie_break h|g|fifo|lifo`, `--per_depth`, `--timeout_sec`, `--include_unsolvable`.

### 1) Core A* vs. IDA* (depths 4…20)

```bash
# P8 & P15 under both heuristics
for H in manhattan linear_conflict; do
  for B in p8 p15; do
    python -m src.experiments.runner --domain $B --algo both       --heuristic $H --depths 4 6 8 10 12 14 16 18 20       --per_depth 16 --timeout_sec 30       --out results/${B}_${H}_both.csv
  done
done

# Rectangles (Manhattan)
python -m src.experiments.runner --rows 3 --cols 4 --algo both   --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20   --per_depth 16 --timeout_sec 30 --out results/r3x4_manhattan_both.csv

python -m src.experiments.runner --rows 3 --cols 5 --algo both   --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20   --per_depth 16 --timeout_sec 30 --out results/r3x5_manhattan_both.csv
```

### 2) IDA* ± BPMX (example on P15)

```bash
python -m src.experiments.runner --domain p15 --algo ida --bpmx   --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20   --per_depth 16 --timeout_sec 30 --out results/p15_ida_manhattan_bpmx.csv

python -m src.experiments.runner --domain p15 --algo ida   --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20   --per_depth 16 --timeout_sec 30 --out results/p15_ida_manhattan_plain.csv
```

### 3) BFS / DFS baselines

```bash
for B in p8 p15; do
  python -m src.experiments.runner --domain $B --algo bfs     --heuristic manhattan --depths 4 6 8 10 12 14 --per_depth 16     --timeout_sec 30 --out results/${B}_bfs.csv

  python -m src.experiments.runner --domain $B --algo dfs     --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20 --per_depth 16     --dfs_max_depth 20 --timeout_sec 30 --out results/${B}_dfs.csv
done

# Rectangles analogous (bfs/dfs with --rows/--cols)
```

### 4) Solvable vs. Unsolvable (IDA*, Manhattan)

```bash
for B in p8 p15; do
  python -m src.experiments.runner --domain $B --algo ida     --heuristic manhattan --include_unsolvable     --depths 4 6 8 10 12 14 16 18 20 --per_depth 12 --timeout_sec 30     --out results/${B}_unsolv_manhattan.csv
done

python -m src.experiments.runner --rows 3 --cols 4 --algo ida   --heuristic manhattan --include_unsolvable   --depths 4 6 8 10 12 14 16 18 20 --per_depth 12 --timeout_sec 30   --out results/r3x4_unsolv_manhattan.csv

python -m src.experiments.runner --rows 3 --cols 5 --algo ida   --heuristic manhattan --include_unsolvable   --depths 4 6 8 10 12 14 16 18 20 --per_depth 12 --timeout_sec 30   --out results/r3x5_unsolv_manhattan.csv
```

### 5) 🧪 A* tie‑breaking ablation (P15, Manhattan, depths 4…20)

```bash
for TB in h g fifo lifo; do
  python -m src.experiments.runner --algo astar --domain p15     --heuristic manhattan --tie_break $TB     --depths 4 6 8 10 12 14 16 18 20 --per_depth 24 --timeout_sec 60     --out results/p15_tie_${TB}.csv
done
```

> Checks robustness of A\* to the OPEN queue tie‑break policy.  
> Plots are created by `report/tie_break_plot.py` (see next section).

---

## 📈 Make the figures & appendix tables

Each script scans `results/`, aggregates (mean + SEM), and writes PNG/XLSX.

```bash
# A* vs. IDA* crossover & per‑board ratio grid
python report/crossover_plots.py

# BPMX impact on IDA* (grid + across‑board)
python report/bpmx_plots.py

# BFS vs. DFS (time + expansions)
python report/bfs_dfs_grid.py

# Duplicates + memory proxies (two grids) + appendix XLSX
python report/duplicates_graphs.py

# Solvable vs. Unsolvable (grid + ratio) + appendix XLSX
python report/unsolve_plots_fix.py

# Cross‑puzzle summary bars (geo‑mean ratio + win‑fraction)
python report/cross_puzzle_summary.py

# 🔧 A* tie‑breaking ablation (time + duplicates, depths 4..20)
python report/tie_break_plot.py
```

Outputs appear in:

```
report/figs/*.png
report/tables/*.csv, *.xlsx
```

---

## 🧵 SLURM example (optional)

```bash
#!/bin/bash
#SBATCH --time 0-04:00:00
#SBATCH --job-name astar_ida
#SBATCH --output job-%J.out
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8

cd /path/to/astar_idastar_puzzle
# conda activate astar

python -m src.experiments.runner --domain p15 --algo both   --heuristic manhattan --depths 4 6 8 10 12 14 16 18 20   --per_depth 16 --timeout_sec 30 --out results/p15_manhattan_both.csv
```

> For long sweeps, shard by depth (one CSV per depth) and merge afterward—more robust to pre‑emption.

---

## 🧠 Tips

- If a curve is missing, you likely don’t have CSVs for that (board, depth, variant).  
- DFS: set `--dfs_max_depth` to avoid recursion blow‑ups.  
- Error bars are **SEM** by default; change in the plotting code if you prefer 95% CI.  
- The plotting scripts are **read‑only** on data—no re‑runs required for tables.

---

## 📜 License & citation

If you use this repo, please cite:

> *A\* vs. IDA\* on Sliding‑Tile Puzzles*, 2025. GitHub repository.

---

## 🙌 Acknowledgements

Course project — *Search in AI*. Thanks to the teaching staff for guidance and an awesome opportunity.  
Happy puzzling! 🧠✨
