from collections import deque
from time import perf_counter
from typing import Tuple, Callable, List, Optional, Set, Dict

State = Tuple[int, ...]

def bfs(start: State, goal: State,
        neighbors_fn: Callable[[State], List[Tuple[State,int]]],
        timeout_sec: float | None = None):
    t0 = perf_counter()
    q = deque([start])
    parent: Dict[State, Optional[State]] = {start: None}
    expanded = generated = 0
    seen: Set[State] = {start}
    peak = 1
    while q:
        if timeout_sec is not None and (perf_counter() - t0) > timeout_sec:
            return {"path": None, "g": None, "expanded": expanded, "generated": generated,
                    "time": perf_counter()-t0, "algorithm": "BFS", "termination": "timeout"}
        peak = max(peak, len(q))
        s = q.popleft()
        if s == goal:
            # reconstruct
            path = []
            g = 0
            while s is not None:
                path.append(s); s = parent[s]; g += 1
            return {"path": list(reversed(path)), "g": g-1, "expanded": expanded, "generated": generated,
                    "time": perf_counter()-t0, "algorithm": "BFS", "termination": "ok"}
        expanded += 1
        for s2,_ in neighbors_fn(s):
            generated += 1
            if s2 in seen: continue
            seen.add(s2); parent[s2] = s; q.append(s2)
    return {"path": None, "g": None, "expanded": expanded, "generated": generated,
            "time": perf_counter()-t0, "algorithm": "BFS", "termination": "exhausted"}
