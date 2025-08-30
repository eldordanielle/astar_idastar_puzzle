#!/usr/bin/env python3
import argparse, os
from pathlib import Path
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from typing import Tuple, List, Optional

from src.domains.puzzle8 import GOAL as GOAL8, scramble as scramble8
from src.domains.puzzlen import NPuzzle
from src.search.a_star import a_star
from src.search.ida_star import ida_star

State = Tuple[int, ...]

def draw_board(state: State, n: int, out_path: Path):
    plt.figure(figsize=(3,3))
    ax = plt.gca()
    ax.set_xlim(0, n); ax.set_ylim(0, n)
    ax.set_xticks([]); ax.set_yticks([]); ax.invert_yaxis()
    # grid
    for i in range(n+1):
        ax.plot([0,n],[i,i], linewidth=1)
        ax.plot([i,i],[0,n], linewidth=1)
    # tiles
    for idx, t in enumerate(state):
        if t == 0: continue
        r, c = divmod(idx, n)
        ax.text(c+0.5, r+0.6, str(t), ha="center", va="center", fontsize=16)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()

def main():
    p = argparse.ArgumentParser(description="Solve one instance and save board images along the path.")
    p.add_argument("--algo", choices=["a","ida"], default="a")
    p.add_argument("--heuristic", choices=["manhattan","linear_conflict"], default="manhattan")
    p.add_argument("--domain", choices=["p8","p15"], default="p8")
    p.add_argument("--n", type=int, default=None)
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--bpmx", action="store_true")
    p.add_argument("--outdir", default="report/figs/example_path")
    args = p.parse_args()

    dom = NPuzzle(args.n) if args.n else (NPuzzle(4) if args.domain=="p15" else NPuzzle(3))
    if dom.N == 3:
        start = scramble8(args.depth, args.seed)
        goal = GOAL8
        if args.heuristic == "manhattan":
            h = dom.manhattan
        else:
            h = dom.linear_conflict
        # use default 8-puzzle neighbors (search modules have fallback)
        neighbors = None
    else:
        start = dom.scramble(args.depth, args.seed)
        goal = dom.GOAL
        h = dom.manhattan if args.heuristic=="manhattan" else dom.linear_conflict
        neighbors = dom.neighbors

    if args.algo == "a":
        res = a_star(start, goal, h, neighbors_fn=neighbors, tie_break="h", return_path=True)
    else:
        res = ida_star(start, goal, h, neighbors_fn=neighbors, use_bpmx=args.bpmx, return_path=True)

    if not res.get("path"):
        print("No path (timeout or exhausted). Try smaller depth.")
        return

    outdir = Path(args.outdir)
    n = dom.N
    for i, s in enumerate(res["path"]):
        draw_board(s, n, outdir / f"step_{i:03d}.png")
    print(f"Saved {len(res['path'])} frames to {outdir}")

if __name__ == "__main__":
    main()
