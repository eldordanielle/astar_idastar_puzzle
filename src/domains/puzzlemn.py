from __future__ import annotations
from typing import Tuple, List, Dict
import random

State = Tuple[int, ...]

class RectPuzzle:
    """
    Generic R×C sliding-tile puzzle (0 is blank).
    Works for 3×3 (8-puzzle), 3×4 (often called 12-puzzle board), 4×4 (15-puzzle), etc.
    """
    def __init__(self, rows: int, cols: int):
        assert rows >= 2 and cols >= 2
        self.R = rows
        self.C = cols
        self.size = rows * cols
        self.GOAL: State = tuple(list(range(1, self.size)) + [0])

        # Precompute neighbor indices for the blank
        self._nei: Dict[int, Tuple[int, ...]] = {}
        for i in range(self.size):
            r, c = divmod(i, self.C)
            moves = []
            if r > 0:             moves.append(i - self.C)
            if r < self.R - 1:    moves.append(i + self.C)
            if c > 0:             moves.append(i - 1)
            if c < self.C - 1:    moves.append(i + 1)
            self._nei[i] = tuple(moves)

        # Goal positions for each tile
        self._goal_pos: Dict[int, Tuple[int, int]] = {}
        for t in range(1, self.size):
            idx = t - 1
            self._goal_pos[t] = (idx // self.C, idx % self.C)

    # ---------- transitions ----------
    def neighbors(self, s: State) -> List[Tuple[State, int]]:
        z = s.index(0)
        out: List[Tuple[State, int]] = []
        for j in self._nei[z]:
            lst = list(s)
            lst[z], lst[j] = lst[j], lst[z]
            out.append((tuple(lst), 1))
        return out

    # ---------- instance generation ----------
    def scramble(self, depth: int, seed: int) -> State:
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

    # ---------- solvability ----------
    def is_solvable(self, s: State) -> bool:
        """
        Standard parity rule:
        - If width (cols) is odd  -> inversions even.
        - If width is even        -> (inversions + blank_row_from_bottom) is ODD.
        """
        arr = [x for x in s if x != 0]
        inv = 0
        for i in range(len(arr)):
            for j in range(i + 1, len(arr)):
                if arr[i] > arr[j]:
                    inv += 1
        if self.C % 2 == 1:
            return (inv % 2) == 0
        # width even
        blank_row_top_idx = s.index(0) // self.C
        blank_row_from_bottom = self.R - blank_row_top_idx  # 1-based
        return ((inv + blank_row_from_bottom) % 2) == 1

    # ---------- heuristics ----------
    def manhattan(self, s: State) -> int:
        dist = 0
        for idx, t in enumerate(s):
            if t == 0: continue
            r, c = divmod(idx, self.C)
            gr, gc = self._goal_pos[t]
            dist += abs(r - gr) + abs(c - gc)
        return dist

    def linear_conflict(self, s: State) -> int:
        m = self.manhattan(s)
        R, C = self.R, self.C
        # Row conflicts
        for r in range(R):
            row = s[r * C:(r + 1) * C]
            tiles = [(c, t) for c, t in enumerate(row)
                     if t != 0 and self._goal_pos[t][0] == r]
            for i in range(len(tiles)):
                ci, ti = tiles[i]; gi = self._goal_pos[ti][1]
                for j in range(i + 1, len(tiles)):
                    cj, tj = tiles[j]; gj = self._goal_pos[tj][1]
                    if gi > gj: m += 2
        # Column conflicts
        for c in range(C):
            col = [s[c + r * C] for r in range(R)]
            tiles = [(r, t) for r, t in enumerate(col)
                     if t != 0 and self._goal_pos[t][1] == c]
            for i in range(len(tiles)):
                ri, ti = tiles[i]; gi = self._goal_pos[ti][0]
                for j in range(i + 1, len(tiles)):
                    rj, tj = tiles[j]; gj = self._goal_pos[tj][0]
                    if gi > gj: m += 2
        return m
