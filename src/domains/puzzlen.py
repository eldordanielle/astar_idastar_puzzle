from __future__ import annotations
from typing import Tuple, List, Dict
import random

State = Tuple[int, ...]

class NPuzzle:
    """Generic N×N sliding-tile puzzle (0 is the blank)."""
    def __init__(self, n: int):
        assert n >= 2
        self.N = n
        self.size = n * n
        self.GOAL: State = tuple(list(range(1, self.size)) + [0])
        # Precompute neighbors for blank moves
        self._nei: Dict[int, Tuple[int, ...]] = {}
        for i in range(self.size):
            r, c = divmod(i, n)
            moves = []
            if r > 0:       moves.append(i - n)
            if r < n - 1:   moves.append(i + n)
            if c > 0:       moves.append(i - 1)
            if c < n - 1:   moves.append(i + 1)
            self._nei[i] = tuple(moves)
        # Goal positions for each tile
        self._goal_pos: Dict[int, Tuple[int, int]] = {}
        for t in range(1, self.size):
            idx = t - 1
            self._goal_pos[t] = (idx // n, idx % n)

    # ---------- Core dynamics ----------
    def neighbors(self, s: State) -> List[Tuple[State, int]]:
        """Return list of (next_state, cost). Unit edge costs."""
        z = s.index(0)
        out: List[Tuple[State, int]] = []
        for j in self._nei[z]:
            lst = list(s)
            lst[z], lst[j] = lst[j], lst[z]
            out.append((tuple(lst), 1))
        return out

    # ---------- Instance generation ----------
    def scramble(self, depth: int, seed: int) -> State:
        """Depth-limited random walk from GOAL with no immediate backtrack."""
        rng = random.Random(seed)
        s = self.GOAL
        last_blank = None
        for _ in range(depth):
            z = s.index(0)
            cand = list(self._nei[z])
            if last_blank in cand and len(cand) > 1:
                cand.remove(last_blank)
            j = rng.choice(cand)
            lst = list(s)
            lst[z], lst[j] = lst[j], lst[z]
            last_blank = z
            s = tuple(lst)
        return s

    def is_solvable(self, s: State) -> bool:
        """Solvability rules:
           - N odd: inversions must be even
           - N even: (inversions + blank_row_from_bottom) must be ODD
             (row count is 1-based from the bottom)
        """
        arr = [x for x in s if x != 0]
        inv = 0
        for i in range(len(arr)):
            for j in range(i + 1, len(arr)):
                if arr[i] > arr[j]:
                    inv += 1
        if self.N % 2 == 1:
            return (inv % 2) == 0
        # even N
        blank_row_top_idx = s.index(0) // self.N  # 0-based from top
        blank_row_from_bottom = self.N - blank_row_top_idx  # 1-based from bottom
        # Correct parity condition for 4x4:
        # Goal has inv=0 and blank_row_from_bottom=1 (odd) -> solvable
        return ((inv + blank_row_from_bottom) % 2) == 1

    # ---------- Heuristics ----------
    def manhattan(self, s: State) -> int:
        dist = 0
        for idx, tile in enumerate(s):
            if tile == 0:
                continue
            r, c = divmod(idx, self.N)
            gr, gc = self._goal_pos[tile]
            dist += abs(r - gr) + abs(c - gc)
        return dist

    def linear_conflict(self, s: State) -> int:
        """Manhattan + 2 per pair of linearly-conflicting tiles (rows & cols)."""
        m = self.manhattan(s)
        N = self.N
        # Row conflicts
        for r in range(N):
            row = s[r * N:(r + 1) * N]
            tiles = [(c, t) for c, t in enumerate(row) if t != 0 and self._goal_pos[t][0] == r]
            for i in range(len(tiles)):
                ci, ti = tiles[i]
                gi = self._goal_pos[ti][1]
                for j in range(i + 1, len(tiles)):
                    cj, tj = tiles[j]
                    gj = self._goal_pos[tj][1]
                    if gi > gj:
                        m += 2
        # Column conflicts
        for c in range(N):
            col = [s[c + r * N] for r in range(N)]
            tiles = [(r, t) for r, t in enumerate(col) if t != 0 and self._goal_pos[t][1] == c]
            for i in range(len(tiles)):
                ri, ti = tiles[i]
                gi = self._goal_pos[ti][0]
                for j in range(i + 1, len(tiles)):
                    rj, tj = tiles[j]
                    gj = self._goal_pos[tj][0]
                    if gi > gj:
                        m += 2
        return m
