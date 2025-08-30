from __future__ import annotations
from typing import Tuple, List, Dict
import random

State = Tuple[int, ...]  # 9-length tuple, 0 is blank
GOAL: State = (1,2,3,4,5,6,7,8,0)

# Precomputed neighbors (blank moves) on 3x3 grid
_NEI = {
    0: (1, 3),
    1: (0, 2, 4),
    2: (1, 5),
    3: (0, 4, 6),
    4: (1, 3, 5, 7),
    5: (2, 4, 8),
    6: (3, 7),
    7: (4, 6, 8),
    8: (5, 7),
}

def neighbors(s: State) -> List[Tuple[State, int]]:
    """Return list of (next_state, cost) pairs with unit cost."""
    i = s.index(0)
    out: List[Tuple[State, int]] = []
    for j in _NEI[i]:
        lst = list(s)
        lst[i], lst[j] = lst[j], lst[i]
        out.append((tuple(lst), 1))
    return out

def is_solvable(s: State) -> bool:
    """8-puzzle solvability: parity of inversions must be even."""
    arr = [x for x in s if x != 0]
    inv = 0
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] > arr[j]:
                inv += 1
    return (inv % 2) == 0

def scramble(depth: int, seed: int) -> State:
    """Scramble GOAL by performing 'depth' random legal blank moves (no immediate backtracks)."""
    rng = random.Random(seed)
    s = GOAL
    last_blank = None
    for _ in range(depth):
        z = s.index(0)
        cand = list(_NEI[z])
        if last_blank in cand and len(cand) > 1:
            cand.remove(last_blank)
        j = rng.choice(cand)
        lst = list(s)
        lst[z], lst[j] = lst[j], lst[z]
        last_blank = z
        s = tuple(lst)
    return s

# ---------------- Heuristics ----------------

_goal_pos: Dict[int, Tuple[int, int]] = {GOAL[i]: (i // 3, i % 3) for i in range(9)}

def manhattan(s: State) -> int:
    """Sum of Manhattan distances to goal positions (blank ignored)."""
    dist = 0
    for idx, tile in enumerate(s):
        if tile == 0:
            continue
        r, c = divmod(idx, 3)
        gr, gc = _goal_pos[tile]
        dist += abs(r - gr) + abs(c - gc)
    return dist

def linear_conflict(s: State) -> int:
    """Manhattan + 2 per linear conflict (row & column)."""
    m = manhattan(s)
    # Row conflicts
    for r in range(3):
        row = s[3*r:3*r+3]
        tiles = [(c, t) for c, t in enumerate(row) if t != 0 and _goal_pos[t][0] == r]
        for i in range(len(tiles)):
            ci, ti = tiles[i]
            gi = _goal_pos[ti][1]
            for j in range(i+1, len(tiles)):
                cj, tj = tiles[j]
                gj = _goal_pos[tj][1]
                if gi > gj:
                    m += 2
    # Column conflicts
    for c in range(3):
        col = [s[c + 3*r] for r in range(3)]
        tiles = [(r, t) for r, t in enumerate(col) if t != 0 and _goal_pos[t][1] == c]
        for i in range(len(tiles)):
            ri, ti = tiles[i]
            gi = _goal_pos[ti][0]
            for j in range(i+1, len(tiles)):
                rj, tj = tiles[j]
                gj = _goal_pos[tj][0]
                if gi > gj:
                    m += 2
    return m
