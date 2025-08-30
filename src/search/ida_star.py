from __future__ import annotations
from typing import Callable, Dict, Tuple, List, Optional, Set
from time import perf_counter
import math

State = Tuple[int, ...]

# default (8-puzzle) fallback
try:
    from src.domains.puzzle8 import neighbors as default_neighbors
except Exception:
    try:
        from domains.puzzle8 import neighbors as default_neighbors
    except Exception:
        from puzzle8 import neighbors as default_neighbors

def reconstruct_path(parents: Dict[State, Optional[State]], goal: State) -> List[State]:
    path: List[State] = []
    s = goal
    while s is not None:
        path.append(s)
        s = parents.get(s)
    return list(reversed(path))

def ida_star(
    start: State,
    goal: State,
    hfun: Callable[[State], int],
    neighbors_fn: Optional[Callable[[State], List[Tuple[State, int]]]] = None,
    use_bpmx: bool = False,
    return_path: bool = True,
    timeout_sec: float | None = None,
):
    """
    IDA* with optional forward-BPMX, instrumentation, and duplicate counting.
    neighbors_fn: callable(state) -> [(next_state, cost)], defaults to 8-puzzle neighbor function.
    """
    neighbors = neighbors_fn or default_neighbors
    t0 = perf_counter()
    TIMEOUT = object()

    expanded = 0
    generated = 0
    duplicates = 0
    ever_seen: Set[State] = set()
    parents: Dict[State, Optional[State]] = {start: None}
    max_depth = 0
    solution_g: Optional[int] = None

    # def dfs(state: State, g: int, bound: int, h_s: int, depth: int, pathset: Set[State]):
    #     nonlocal expanded, generated, duplicates, max_depth, solution_g
    #     if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
    #         return TIMEOUT

    #     max_depth = max(max_depth, depth)
    #     f = g + h_s
    #     if f > bound:
    #         return f
    #     if state == goal:
    #         solution_g = g
    #         return -1

    #     expanded += 1
    #     min_next = math.inf

    #     for s2, c in neighbors(state):
    #         if s2 in pathset:
    #             continue
    #         g2 = g + c
    #         h2 = hfun(s2)
    #         if use_bpmx:
    #             h2 = max(h2, h_s - c)

    #         generated += 1
    #         if s2 in ever_seen:
    #             duplicates += 1
    #         else:
    #             ever_seen.add(s2)

    #         parents[s2] = state
    #         pathset.add(s2)
    #         t = dfs(s2, g2, bound, h2, depth + 1, pathset)
    #         if t is TIMEOUT:
    #             return TIMEOUT
    #         if t == -1:
    #             return -1
    #         if t < min_next:
    #             min_next = t
    #         pathset.remove(s2)

    #     return min_next

    def dfs(state: State, g: int, bound: int, h_s: int, depth: int, pathset: Set[State]):
        """
        Depth-first step for IDA* with optional BPMX.

        - f = g + h_s pruning at entry
        - child -> parent raise (BPMX) before exploring a child
            * if raise makes g + h_parent > bound -> early cutoff (prune remaining siblings)
        - parent -> child bump (pathmax down) before recursing
        - returns:
            * TIMEOUT sentinel   if timeout
            * -1                 if goal found
            * next_min_bound     (float) the minimal f that exceeded 'bound' among this subtree
        """
        nonlocal expanded, generated, duplicates, max_depth, solution_g
        if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
            return TIMEOUT

        max_depth = max(max_depth, depth)
        f_here = g + h_s
        if f_here > bound:
            return f_here
        if state == goal:
            solution_g = g
            return -1

        expanded += 1
        min_next = math.inf

        # Keep a mutable parent h we can raise as children reveal larger heuristics
        h_parent = h_s

        # Iterate children
        for idx, (s2, c) in enumerate((neighbors_fn or default_neighbors)(state) if neighbors_fn else default_neighbors(state)):
            if s2 in pathset:
                continue

            g2 = g + c
            h2_raw = hfun(s2)

            if use_bpmx:
                # -------- BPMX child -> parent raise --------
                # If child looks much harder than parent, raise parent's h
                maybe_parent = h2_raw - c
                if maybe_parent > h_parent:
                    h_parent = maybe_parent
                    # Early prune remaining siblings if parent now exceeds bound
                    if g + h_parent > bound:
                        # Return the cutoff value so caller can update next bound
                        return g + h_parent

                # -------- BPMX parent -> child bump (pathmax down) --------
                h2 = max(h2_raw, h_parent - c)
            else:
                h2 = h2_raw

            generated += 1
            if s2 in ever_seen:
                duplicates += 1
            else:
                ever_seen.add(s2)

            parents[s2] = state
            pathset.add(s2)

            t = dfs(s2, g2, bound, h2, depth + 1, pathset)

            if t is TIMEOUT:
                return TIMEOUT
            if t == -1:
                return -1
            if t < min_next:
                min_next = t

            pathset.remove(s2)

        return min_next


    h0 = hfun(start)
    bound = h0
    ever_seen.add(start)

    while True:
        pathset: Set[State] = {start}
        t = dfs(start, 0, bound, h0, 0, pathset)
        if t is TIMEOUT:
            return {
                "path": None, "g": None,
                "expanded": expanded, "generated": generated, "duplicates": duplicates,
                "peak_recursion": max_depth, "bound_final": bound,
                "time": perf_counter() - t0,
                "algorithm": "IDA* (BPMX ON)" if use_bpmx else "IDA*",
                "termination": "timeout",
            }
        if t == -1:
            t1 = perf_counter()
            return {
                "path": reconstruct_path(parents, goal) if return_path else None,
                "g": solution_g,
                "expanded": expanded,
                "generated": generated,
                "duplicates": duplicates,
                "peak_recursion": max_depth,
                "bound_final": bound,
                "time": t1 - t0,
                "algorithm": "IDA* (BPMX ON)" if use_bpmx else "IDA*",
                "termination": "ok",
            }
        if t == math.inf:
            t1 = perf_counter()
            return {
                "path": None,
                "g": None,
                "expanded": expanded,
                "generated": generated,
                "duplicates": duplicates,
                "peak_recursion": max_depth,
                "bound_final": bound,
                "time": t1 - t0,
                "algorithm": "IDA* (BPMX ON)" if use_bpmx else "IDA*",
                "termination": "exhausted",
            }
        bound = int(t)
