from __future__ import annotations
import argparse, csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Callable, Optional

from src.domains.puzzle8 import (
    GOAL as GOAL8,
    scramble as scramble8,
    is_solvable as solv8,
    manhattan as man8,
    linear_conflict as lc8,
)
from src.domains.puzzlen import NPuzzle
from src.domains.puzzlemn import RectPuzzle
from src.search.a_star import a_star
from src.search.ida_star import ida_star
from src.search.bfs import bfs
from src.search.dfs import dfs

State = Tuple[int, ...]

@dataclass
class Instance:
    seed: int
    depth: int
    state: State

def _gen(inst_scramble, inst_is_solvable, depths: List[int], per_depth: int, start_seed: int = 0) -> List[Instance]:
    out: List[Instance] = []
    seed = start_seed
    for d in depths:
        made = 0
        attempts = 0
        while made < per_depth:
            s = inst_scramble(d, seed)
            seed += 1
            attempts += 1
            if inst_is_solvable(s):
                out.append(Instance(seed=seed, depth=d, state=s))
                made += 1
            if attempts > per_depth * 2000:
                raise RuntimeError(f"Instance generation took too long at depth={d}. Check solvability logic.")
    return out

def make_unsolvable_variant(s: State) -> State:
    lst = list(s)
    i = next(k for k, v in enumerate(lst) if v != 0)
    j = next(k for k, v in enumerate(lst[i + 1 :], start=i + 1) if v != 0)
    lst[i], lst[j] = lst[j], lst[i]
    return tuple(lst)

def choose_domain(args):
    """
    Domain selection precedence:
    --rows/--cols  >  --n  >  --domain (p8|p15).
    Returns (neighbors_fn, hfun, goal, generator_tuple)
    where generator_tuple is (scramble_fn, is_solvable_fn).
    """
    # Rectangular board?
    if args.rows is not None and args.cols is not None:
        dom = RectPuzzle(args.rows, args.cols)
        neighbors_fn = dom.neighbors
        if args.heuristic == "manhattan": hfun = dom.manhattan
        else:                              hfun = dom.linear_conflict
        goal = dom.GOAL
        gen = (dom.scramble, dom.is_solvable)
        return neighbors_fn, hfun, goal, gen

    # Square N×N?
    if args.n is not None:
        dom = NPuzzle(args.n)
        neighbors_fn = dom.neighbors
        if args.heuristic == "manhattan": hfun = dom.manhattan
        else:                              hfun = dom.linear_conflict
        goal = dom.GOAL
        gen = (dom.scramble, dom.is_solvable)
        return neighbors_fn, hfun, goal, gen

    # Predefined p8/p15
    if args.domain == "p15":
        dom = NPuzzle(4)
        neighbors_fn = dom.neighbors
        hfun = dom.manhattan if args.heuristic == "manhattan" else dom.linear_conflict
        goal = dom.GOAL
        gen = (dom.scramble, dom.is_solvable)
        return neighbors_fn, hfun, goal, gen

    # default p8
    # neighbors_fn = None  # search modules know 8-puzzle neighbors by default
    # hfun = man8 if args.heuristic == "manhattan" else lc8
    # goal = GOAL8
    # gen = (scramble8, solv8)
    # return neighbors_fn, hfun, goal, gen
        # default p8
    dom = NPuzzle(3)
    neighbors_fn = dom.neighbors
    hfun = dom.manhattan if args.heuristic == "manhattan" else dom.linear_conflict
    goal = dom.GOAL
    gen = (dom.scramble, dom.is_solvable)
    return neighbors_fn, hfun, goal, gen


def main():
    ap = argparse.ArgumentParser(description="A*/IDA* (+BFS/DFS) N/Rect-puzzle experiment runner")
    ap.add_argument("--algo", choices=["a", "ida", "bfs", "dfs", "both", "all"], default="both",
                    help="'both' = A*+IDA*, 'all' = A*+IDA*+BFS+DFS")
    ap.add_argument("--heuristic", choices=["manhattan","linear_conflict"], default="manhattan")
    ap.add_argument("--depths", type=int, nargs="+", default=[6,10,14,18,22,26])
    ap.add_argument("--per_depth", type=int, default=30)
    ap.add_argument("--bpmx", action="store_true", help="Enable BPMX for IDA*")
    ap.add_argument("--tie_break", choices=["h","g","fifo","lifo"], default="h")
    ap.add_argument("--timeout_sec", type=float, default=None, help="Per-instance wall time")
    ap.add_argument("--dfs_max_depth", type=int, default=None, help="Depth limit for DFS (optional)")
    ap.add_argument("--out", type=Path, default=Path("results/last_run.csv"))

    # domain selection
    ap.add_argument("--domain", choices=["p8","p15"], default="p8", help="3x3 or 4x4 shortcut")
    ap.add_argument("--n", type=int, default=None, help="Square board size (N×N)")
    ap.add_argument("--rows", type=int, default=None, help="Rows for rectangular board")
    ap.add_argument("--cols", type=int, default=None, help="Cols for rectangular board")

    ap.add_argument("--include_unsolvable", action="store_true", help="Also test unsolvable variants (p8 recommended)")
    args = ap.parse_args()

    neighbors_fn, hfun, goal, gen = choose_domain(args)
    scramble_fn, solvable_fn = gen

    insts = _gen(scramble_fn, solvable_fn, args.depths, args.per_depth)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "algorithm","heuristic","depth","seed",
        "expanded","generated","duplicates","g","time_sec",
        "peak_open","peak_closed","peak_recursion","bound_final","tie_break",
        "termination","solvable"
    ]

    def write_row(w, res, heur, inst: Instance, solvable_flag: int):
        w.writerow([
            res.get("algorithm",""), heur, inst.depth, inst.seed,
            res.get("expanded",""), res.get("generated",""), res.get("duplicates",""), res.get("g",""),
            f"{res.get('time',0.0):.6f}",
            res.get("peak_open",""), res.get("peak_closed",""), res.get("peak_recursion",""), res.get("bound_final",""),
            res.get("tie_break",""), res.get("termination","ok"), solvable_flag
        ])

    want_a   = args.algo in ("a","both","all")
    want_ida = args.algo in ("ida","both","all")
    want_bfs = args.algo in ("bfs","all")
    want_dfs = args.algo in ("dfs","all")

    with args.out.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(header)
        for inst in insts:
            # Solvable instance
            if want_a:
                r = a_star(inst.state, goal, hfun, neighbors_fn=neighbors_fn,
                           tie_break=args.tie_break, return_path=False, timeout_sec=args.timeout_sec)
                write_row(w, r, args.heuristic, inst, 1)
            if want_ida:
                r = ida_star(inst.state, goal, hfun, neighbors_fn=neighbors_fn,
                             use_bpmx=args.bpmx, return_path=False, timeout_sec=args.timeout_sec)
                write_row(w, r, args.heuristic, inst, 1)
            if want_bfs and neighbors_fn is not None:
                r = bfs(inst.state, goal, neighbors_fn=neighbors_fn, timeout_sec=args.timeout_sec)
                write_row(w, r, args.heuristic, inst, 1)
            if want_dfs and neighbors_fn is not None:
                r = dfs(inst.state, goal, neighbors_fn=neighbors_fn,
                        max_depth=args.dfs_max_depth, timeout_sec=args.timeout_sec)
                write_row(w, r, args.heuristic, inst, 1)

            # Optional unsolvable variants (flip parity).
            # Always do A*/IDA*; only do BFS/DFS when neighbors_fn is available.
            if args.include_unsolvable:
                u = make_unsolvable_variant(inst.state)

                if want_a:
                    r = a_star(u, goal, hfun, neighbors_fn=neighbors_fn,
                               tie_break=args.tie_break, return_path=False, timeout_sec=args.timeout_sec)
                    write_row(w, r, args.heuristic, inst, 0)

                if want_ida:
                    r = ida_star(u, goal, hfun, neighbors_fn=neighbors_fn,
                                 use_bpmx=args.bpmx, return_path=False, timeout_sec=args.timeout_sec)
                    write_row(w, r, args.heuristic, inst, 0)

                if want_bfs and neighbors_fn is not None:
                    r = bfs(u, goal, neighbors_fn=neighbors_fn, timeout_sec=args.timeout_sec)
                    write_row(w, r, args.heuristic, inst, 0)

                if want_dfs and neighbors_fn is not None:
                    r = dfs(u, goal, neighbors_fn=neighbors_fn,
                            max_depth=args.dfs_max_depth, timeout_sec=args.timeout_sec)
                    write_row(w, r, args.heuristic, inst, 0)

    print(f"Wrote {args.out} ({len(insts)} instances)")

if __name__ == "__main__":
    main()
