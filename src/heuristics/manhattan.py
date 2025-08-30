# from typing import Tuple
# State = Tuple[int, ...]

# def manhattan(s: State) -> int:
#     dist = 0
#     for idx, tile in enumerate(s):
#         if tile == 0:
#             continue
#         goal_idx = tile - 1
#         r1, c1 = divmod(idx, 3)
#         r2, c2 = divmod(goal_idx, 3)
#         dist += abs(r1 - r2) + abs(c1 - c2)
#     return dist


from typing import Tuple
from src.domains.puzzle8 import manhattan as _manhattan

State = Tuple[int, ...]

def manhattan(s: State) -> int:
    return _manhattan(s)
