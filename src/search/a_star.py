from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, List, Set
import heapq
from time import perf_counter
import math
import itertools

State = Tuple[int, ...]

# default (8-puzzle) fallback
try:
    from src.domains.puzzle8 import neighbors as default_neighbors
except Exception:
    try:
        from domains.puzzle8 import neighbors as default_neighbors
    except Exception:
        from puzzle8 import neighbors as default_neighbors

def reconstruct_path(node: "PQItem") -> List[State]:
    path: List[State] = []
    while node is not None:
        path.append(node.state)
        node = node.parent  # type: ignore[attr-defined]
    path.reverse()
    return path

@dataclass
class PQItem:
    f: int
    h: int
    g: int
    state: State
    parent: Optional["PQItem"] = None

def a_star(
    start: State,
    goal: State,
    hfun: Callable[[State], int],
    neighbors_fn: Optional[Callable[[State], List[Tuple[State, int]]]] = None,
    tie_break: str = "h",
    return_path: bool = True,
    timeout_sec: float | None = None,
):
    """
    A* with instrumentation.
    neighbors_fn: callable(state) -> [(next_state, cost)], defaults to 8-puzzle neighbor function.
    """
    neighbors = neighbors_fn or default_neighbors
    t0 = perf_counter()

    open_heap: List[Tuple[Tuple[int, int, int], int, PQItem]] = []
    counter = itertools.count()

    def priority_tuple(f: int, g: int, h: int, ctr: int) -> Tuple[int, int, int]:
        if tie_break == "h":   return (f, h, ctr)
        if tie_break == "g":   return (f, -g, ctr)
        if tie_break == "fifo":return (f, 0,  ctr)
        if tie_break == "lifo":return (f, 0, -ctr)
        return (f, h, ctr)

    h0 = hfun(start)
    start_item = PQItem(f=h0, h=h0, g=0, state=start, parent=None)
    heapq.heappush(open_heap, (priority_tuple(h0, 0, h0, next(counter)), next(counter), start_item))

    best_g: Dict[State, int] = {start: 0}
    closed: Set[State] = set()

    expanded = 0
    generated = 0
    duplicates = 0
    seen_ever: Set[State] = {start}

    peak_open = 1
    peak_closed = 0

    while open_heap:
        if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
            return {
                "path": None, "g": None,
                "expanded": expanded, "generated": generated, "duplicates": duplicates,
                "peak_open": peak_open, "peak_closed": peak_closed,
                "time": perf_counter() - t0,
                "algorithm": "A*",
                "tie_break": tie_break,
                "termination": "timeout",
            }

        peak_open = max(peak_open, len(open_heap))
        _, _, node = heapq.heappop(open_heap)
        if node.state in closed:
            continue

        if node.state == goal:
            t1 = perf_counter()
            return {
                "path": reconstruct_path(node) if return_path else None,
                "g": node.g,
                "expanded": expanded,
                "generated": generated,
                "duplicates": duplicates,
                "peak_open": peak_open,
                "peak_closed": peak_closed,
                "time": t1 - t0,
                "algorithm": "A*",
                "tie_break": tie_break,
                "termination": "ok",
            }

        closed.add(node.state)
        expanded += 1
        peak_closed = max(peak_closed, len(closed))

        for s2, c in neighbors(node.state):
            g2 = node.g + c
            h2 = hfun(s2)
            f2 = g2 + h2
            generated += 1
            if s2 in seen_ever:
                duplicates += 1
            else:
                seen_ever.add(s2)

            if g2 < best_g.get(s2, math.inf):
                best_g[s2] = g2
                child = PQItem(f=f2, h=h2, g=g2, state=s2, parent=node)
                pr = priority_tuple(f2, g2, h2, next(counter))
                heapq.heappush(open_heap, (pr, next(counter), child))

    # Open exhausted without finding goal
    t1 = perf_counter()
    return {
        "path": None,
        "g": None,
        "expanded": expanded,
        "generated": generated,
        "duplicates": duplicates,
        "peak_open": peak_open,
        "peak_closed": peak_closed,
        "time": t1 - t0,
        "algorithm": "A*",
        "tie_break": tie_break,
        "termination": "exhausted",
    }
