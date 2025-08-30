# from typing import Tuple
# from .manhattan import manhattan
# State = Tuple[int, ...]

# def linear_conflict(s: State) -> int:
#     h = manhattan(s)
#     # rows
#     for r in range(3):
#         tiles = s[3*r:3*r+3]
#         goal_cols = []
#         for c, tile in enumerate(tiles):
#             if tile != 0 and (tile-1)//3 == r:
#                 goal_cols.append((c, tile))
#         for i in range(len(goal_cols)):
#             ci, ti = goal_cols[i]
#             gi = (ti-1) % 3
#             for j in range(i+1, len(goal_cols)):
#                 cj, tj = goal_cols[j]
#                 gj = (tj-1) % 3
#                 if gi > gj:
#                     h += 2
#     # cols
#     for c in range(3):
#         col = [s[c], s[c+3], s[c+6]]
#         goal_rows = []
#         for r, tile in enumerate(col):
#             if tile != 0 and (tile-1) % 3 == c:
#                 goal_rows.append((r, tile))
#         for i in range(len(goal_rows)):
#             ri, ti = goal_rows[i]
#             gi = (ti-1)//3
#             for j in range(i+1, len(goal_rows)):
#                 rj, tj = goal_rows[j]
#                 gj = (tj-1)//3
#                 if gi > gj:
#                     h += 2
#     return h


from typing import Tuple
from src.domains.puzzle8 import linear_conflict as _linear_conflict

State = Tuple[int, ...]

def linear_conflict(s: State) -> int:
    return _linear_conflict(s)

