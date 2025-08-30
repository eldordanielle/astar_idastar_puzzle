#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path

def run(desc, cmd):
    print(f"\n=== {desc} ===\n{cmd}")
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        sys.exit(r.returncode)

def main():
    Path("results").mkdir(exist_ok=True)
    run("Manhattan both", "python -m src.experiments.runner --depths 6 10 14 18 --per_depth 20 --heuristic manhattan --algo both --out results/manhattan_final.csv")
    run("LinearConflict both", "python -m src.experiments.runner --depths 6 10 14 18 --per_depth 20 --heuristic linear_conflict --algo both --out results/linear_conflict_final.csv")
    run("IDA* BPMX", "python -m src.experiments.runner --depths 6 10 14 18 --per_depth 20 --heuristic manhattan --algo ida --bpmx --out results/ida_bpmx_final.csv")

if __name__ == "__main__":
    main()
