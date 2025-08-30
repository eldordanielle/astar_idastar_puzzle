# from time import perf_counter
# from typing import Tuple, Callable, List, Optional, Set, Dict

# State = Tuple[int, ...]

# def dfs(start: State, goal: State,
#         neighbors_fn: Callable[[State], List[Tuple[State,int]]],
#         max_depth: int | None = None,
#         timeout_sec: float | None = None):
#     t0 = perf_counter()
#     expanded = generated = 0
#     parent: Dict[State, Optional[State]] = {start: None}
#     pathset: Set[State] = {start}

#     def rec(s: State, depth: int) -> Optional[State]:
#         nonlocal expanded, generated
#         if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
#             return None
#         if s == goal: return s
#         if max_depth is not None and depth >= max_depth: return None
#         expanded += 1
#         for s2,_ in neighbors_fn(s):
#             generated += 1
#             if s2 in pathset: continue
#             parent[s2] = s; pathset.add(s2)
#             r = rec(s2, depth+1)
#             if r is not None: return r
#             pathset.remove(s2)
#         return None

#     end = rec(start, 0)
#     if end is None:
#         term = "timeout" if timeout_sec is not None and (perf_counter()-t0) > timeout_sec else "exhausted"
#         return {"path": None, "g": None, "expanded": expanded, "generated": generated,
#                 "time": perf_counter()-t0, "algorithm": "DFS", "termination": term}
#     # reconstruct
#     path = []; g = 0; s = end
#     while s is not None:
#         path.append(s); s = parent[s]; g += 1
#     return {"path": list(reversed(path)), "g": g-1, "expanded": expanded, "generated": generated,
#             "time": perf_counter()-t0, "algorithm": "DFS", "termination": "ok"}


from __future__ import annotations
from typing import Callable, Dict, Tuple, List, Optional, Set
from time import perf_counter

State = Tuple[int, ...]

def dfs(
    start: State,
    goal: State,
    neighbors_fn: Callable[[State], List[Tuple[State, int]]],
    max_depth: Optional[int] = None,
    timeout_sec: Optional[float] = None,
):
    """
    Iterative DFS with (a) per-path cycle avoidance and (b) optional depth bound.
    Returns a dict with keys used by src/experiments/runner.write_row(...).
    """
    t0 = perf_counter()

    # accounting (align loosely with your other search modules)
    expanded = 0           # count nodes whose children we *started* to iterate
    generated = 0          # count child edges we *considered* (after cycle/bound checks)
    duplicates = 0         # not tracked for DFS baseline (kept for schema)
    peak_depth = 0

    # stack holds: (state, depth, iterator_over_neighbors, expanded_flag)
    # expanded_flag lets us count "expanded" once per node when we first pull a child
    stack: List[Tuple[State, int, object, bool]] = []
    on_path: Set[State] = set()

    # init
    it0 = iter(neighbors_fn(start))
    stack.append((start, 0, it0, False))
    on_path.add(start)

    if start == goal:
        return {
            "path": None, "g": 0,
            "expanded": 0, "generated": 0, "duplicates": 0,
            "peak_recursion": 0, "bound_final": max_depth if max_depth is not None else "",
            "time": perf_counter() - t0,
            "algorithm": "DFS", "termination": "ok",
        }

    while stack:
        # timeout?
        if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
            return {
                "path": None, "g": None,
                "expanded": expanded, "generated": generated, "duplicates": duplicates,
                "peak_recursion": peak_depth, "bound_final": max_depth if max_depth is not None else "",
                "time": perf_counter() - t0,
                "algorithm": "DFS", "termination": "timeout",
            }

        s, d, it, did_expand = stack[-1]
        peak_depth = max(peak_depth, d)

        try:
            s2, cost = next(it)
        except StopIteration:
            # done with s
            on_path.remove(s)
            stack.pop()
            continue

        # enforce depth bound on the *child*
        if (max_depth is not None) and (d + 1 > max_depth):
            continue

        # avoid cycles along current path
        if s2 in on_path:
            duplicates += 1
            continue

        # first time we actually pull a child => count "expanded" for s
        if not did_expand:
            expanded += 1
            stack[-1] = (s, d, it, True)

        generated += 1

        if s2 == goal:
            return {
                "path": None, "g": d + 1,
                "expanded": expanded, "generated": generated, "duplicates": duplicates,
                "peak_recursion": peak_depth, "bound_final": max_depth if max_depth is not None else "",
                "time": perf_counter() - t0,
                "algorithm": "DFS", "termination": "ok",
            }

        # dive deeper
        on_path.add(s2)
        stack.append((s2, d + 1, iter(neighbors_fn(s2)), False))

    # no solution within bound
    return {
        "path": None, "g": None,
        "expanded": expanded, "generated": generated, "duplicates": duplicates,
        "peak_recursion": peak_depth, "bound_final": max_depth if max_depth is not None else "",
        "time": perf_counter() - t0,
        "algorithm": "DFS", "termination": "exhausted",
    }
