#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path

def run(cmd):
    print("Running:", cmd)
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        sys.exit(r.returncode)

def main():
    Path("results").mkdir(exist_ok=True)
    run("python -m src.experiments.runner --depths 6 10 14 --per_depth 10 --heuristic manhattan --algo both --out results/manhattan.csv")
    run("python -m src.experiments.runner --depths 6 10 14 --per_depth 10 --heuristic linear_conflict --algo both --out results/linear_conflict.csv")
    run("python -m src.experiments.runner --depths 6 10 14 --per_depth 10 --heuristic manhattan --algo ida --bpmx --out results/ida_bpmx.csv")

if __name__ == "__main__":
    main()
