#!/usr/bin/env python3
import argparse, csv
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Callable

from src.domains.puzzle8 import GOAL as GOAL8, scramble as scramble8, is_solvable as solv8, manhattan as man8, linear_conflict as lc8
from src.domains.puzzlen import NPuzzle
from src.search.a_star import a_star
from src.search.ida_star import ida_star

@dataclass
class Instance:
    seed: int
    depth: int
    state: Tuple[int, ...]

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

def choose_hfun(name: str, dom: NPuzzle) -> Callable[[Tuple[int, ...]], int]:
    n = name.lower()
    if n in ("manhattan","m"):
        return dom.manhattan if dom.N != 3 else man8
    if n in ("linear","linear_conflict","lc"):
        return dom.linear_conflict if dom.N != 3 else lc8
    raise ValueError(name)

def main():
    p = argparse.ArgumentParser(description="Partner-compatible runner (N-puzzle)")
    p.add_argument("--depths", type=int, nargs="+", default=[6,10,14,18,22,26])
    p.add_argument("--per_depth", type=int, default=10)
    p.add_argument("--heuristic", choices=["manhattan","linear_conflict"], default="manhattan")
    p.add_argument("--algo", choices=["a","ida","both"], default="both")
    p.add_argument("--bpmx", action="store_true")
    p.add_argument("--tie_break", choices=["h","g","fifo","lifo"], default="h")
    p.add_argument("--out", type=Path, default=Path("../../results/last_run.csv"))
    p.add_argument("--domain", choices=["p8","p15"], default="p8")
    p.add_argument("--n", type=int, default=None)
    args = p.parse_args()

    dom = NPuzzle(args.n) if args.n else (NPuzzle(4) if args.domain == "p15" else NPuzzle(3))
    hfun = choose_hfun(args.heuristic, dom)

    if dom.N == 3:
        insts = _gen(scramble8, solv8, args.depths, args.per_depth)
        GOAL = GOAL8
        neighbors_fn = None
    else:
        insts = _gen(dom.scramble, dom.is_solvable, args.depths, args.per_depth)
        GOAL = dom.GOAL
        neighbors_fn = dom.neighbors

    args.out.parent.mkdir(parents=True, exist_ok=True)
    header = ["algorithm","heuristic","depth","seed","expanded","generated","duplicates","g","time_sec","peak_open","peak_closed","peak_recursion","bound_final","tie_break"]
    with args.out.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(header)
        for inst in insts:
            if args.algo in ("a","both"):
                r = a_star(inst.state, GOAL, hfun, neighbors_fn=neighbors_fn, tie_break=args.tie_break, return_path=False)
                w.writerow([r["algorithm"], args.heuristic, inst.depth, inst.seed, r["expanded"], r["generated"], r.get("duplicates",""), r["g"], f"{r['time']:.6f}", r.get("peak_open",""), r.get("peak_closed",""), "", "", r.get("tie_break","")])
            if args.algo in ("ida","both"):
                r = ida_star(inst.state, GOAL, hfun, neighbors_fn=neighbors_fn, use_bpmx=args.bpmx, return_path=False)
                w.writerow([r["algorithm"], args.heuristic, inst.depth, inst.seed, r["expanded"], r["generated"], r.get("duplicates",""), r["g"], f"{r['time']:.6f}", "", "", r.get("peak_recursion",""), r.get("bound_final",""), ""])
    print(f"Wrote {args.out} ({len(insts)} instances)")

if __name__ == "__main__":
    main()
