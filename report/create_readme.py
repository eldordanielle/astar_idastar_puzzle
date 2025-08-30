# write_readme.py
from pathlib import Path

md = """# 🧩 A* vs. IDA* on Sliding-Tile Puzzles (8, 15, 3×4, 3×5)

End-to-end, reproducible experiments comparing **A\\*** and **IDA\\*** under **Manhattan** and **Linear Conflict** heuristics, with **BPMX**, **BFS/DFS** baselines, **solvable vs. unsolvable** analysis, and an **A\\* tie-breaking ablation**.  
All figures and appendix tables are generated from CSVs produced by one runner.

---

## 🔎 What you’ll find

- **A\\* vs. IDA\\***: time, expansions, duplicate rate, and memory proxies across depths **4…20**.  
- **BPMX on IDA\\***: ratio plots (BPMX / Plain).  
- **BFS vs. DFS**: bookend baselines.  
- **Solvable vs. unsolvable**: cost to prove vs. disprove.  
- **A\\* tie-breaking (h/g/fifo/lifo)**: robustness check.  
- Cross-puzzle summary bars + appendix tables (CSV/XLSX).

**Headline:** IDA\\* dominates at shallow–moderate depths; A\\* catches up when `CLOSED` fits (especially with LC). BPMX didn’t help in this Python setting. Unsolvables are a mid-depth constant-factor tax (often ≤2×), not a different growth rate. Tie-breaking in A\\* barely moves the needle.

---

## 📁 Layout

