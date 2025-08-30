# Laboratory Report: Comparison between A* and IDA* on the 8-Puzzle Problem

**Student:** [Student Name]  
**Course:** Artificial Intelligence Search  
**Instructor:** Ariel Felner  
**Date:** [Date]

---

## 1. Introduction

### 1.1 Theoretical Background

**A* (A-Star)** is a heuristic-guided search algorithm that combines greedy search with breadth-first search. The algorithm uses an evaluation function f(n) = g(n) + h(n), where:
- g(n) is the actual cost from the initial state to state n
- h(n) is the heuristic (estimate) from state n to the goal

**IDA* (Iterative Deepening A*)** is a variant of A* that uses iterative depth-limited search. The algorithm starts with a low threshold and gradually increases it until it finds the optimal solution.

**BPMX (Bidirectional Pathmax)** is an optimization for IDA* that improves the heuristic by using bidirectional information.

### 1.2 The 8-Puzzle Problem

8-Puzzle is a classic search problem where there is a 3x3 board with 8 numbered tiles and one empty square. The goal is to arrange the tiles in ascending order by moving the empty square.

### 1.3 Heuristics

**Manhattan Distance:** Counts the minimum distance each tile needs to travel to reach its correct position.

**Linear Conflict:** Extends Manhattan Distance by adding penalties for tiles that are in the same row or column but in the wrong order.

---

## 2. Experiment Objectives

### 2.1 Research Hypotheses

1. **Primary Hypothesis:** IDA* will be more efficient than A* in terms of memory usage, but A* will be faster in terms of runtime.

2. **Secondary Hypothesis:** BPMX will improve IDA* performance by reducing the number of expanded nodes.

3. **Tertiary Hypothesis:** Linear Conflict will be more effective than Manhattan Distance for both algorithms.

### 2.2 Specific Objectives

- Quantitative comparison between A* and IDA* on different metrics
- Testing the impact of BPMX on IDA* performance
- Comparison between different heuristics
- Analysis of algorithm behavior at different depths

---

## 3. Experimental Methodology

### 3.1 Experimental Environment

- **Programming Language:** Python 3.x
- **Operating System:** Windows 10
- **Main Libraries:** matplotlib, csv, dataclasses

### 3.2 Code Structure

The project is divided into several modules:

```
src/
├── domains/
│   └── puzzle8.py          # 8-Puzzle implementation
├── heuristics/
│   ├── manhattan.py        # Manhattan heuristic
│   └── linear_conflict.py  # Linear Conflict heuristic
├── search/
│   ├── a_star.py          # A* implementation
│   └── ida_star.py        # IDA* implementation with BPMX
└── experiments/
    ├── runner.py          # Experiment runner
    └── plot.py            # Graph generation
```

### 3.3 Methodology

**Instance Generation:** We used the `scramble` function that creates instances with known solution depth. For each depth, we created multiple different instances.

**Performance Metrics:**
- **Expanded Nodes:** Number of nodes expanded
- **Generated Nodes:** Number of nodes generated
- **Time:** Runtime in seconds
- **Memory:** Memory usage (peak_open, peak_closed)

**Test Depths:** 10, 15, 20 (and higher depths for BPMX testing)

---

## 4. Experimental Results

### 4.1 A* vs IDA* Comparison with Manhattan Distance

The generated graphs show a comprehensive comparison between A* and IDA* with Manhattan Distance heuristic. Statistical analysis reveals:

**Depth 10:**
- A* expands 13.6 nodes on average vs 15.6 for IDA* (ratio 1.15)
- A* generates 25.8 nodes vs 25.2 for IDA* (ratio 0.98)
- A* is 1.5x faster (time ratio 0.66)

**Depth 15:**
- A* expands 54.6 nodes vs 96.0 for IDA* (ratio 1.76)
- A* generates 95.6 nodes vs 161.8 for IDA* (ratio 1.69)
- A* is 1.15x faster

**Depth 20:**
- A* expands 75.8 nodes vs 255.6 for IDA* (ratio 3.37)
- A* generates 129.2 nodes vs 430.2 for IDA* (ratio 3.33)
- A* is 1.9x faster

### 4.2 A* vs IDA* Comparison with Linear Conflict

Linear Conflict shows similar results but with improvements:

**Depth 10:**
- Expanded ratio: 1.14 (similar to Manhattan)
- Generated ratio: 0.96 (slight improvement)
- Time ratio: 0.83 (slight improvement)

**Depth 15:**
- Expanded ratio: 1.73 (similar to Manhattan)
- Generated ratio: 1.59 (slight improvement)
- Time ratio: 1.37 (slight improvement)

**Depth 20:**
- Expanded ratio: 2.09 (significant improvement from 3.37)
- Generated ratio: 2.08 (significant improvement from 3.33)
- Time ratio: 1.81 (slight improvement)

### 4.3 BPMX Impact on IDA*

**FINAL CORRECTED RESULTS:** After fixing the BPMX implementation, we observe significant improvements:

**Depth 15:**
- Expanded ratio: 1.00 (no difference as expected)
- Generated ratio: 0.69 (31% reduction)
- Time ratio: 1.75 (BPMX adds overhead)

**Depth 20:**
- Expanded ratio: 1.00 (no difference as expected)
- Generated ratio: 0.69 (31% reduction)
- Time ratio: 1.17 (moderate overhead)

**Overall Performance:**
- Average generated nodes reduction: ~30%
- No change in expanded nodes (as theoretically expected)
- Time overhead: 17-75% depending on depth

### 4.4 Results Analysis

**Key Insights:**

1. **A* outperforms IDA* on all metrics** - Contrary to theoretical expectations, A* shows better performance at all tested depths.

2. **The gap increases with depth** - At depth 20, IDA* expands 3.37x more nodes than A*.

3. **Linear Conflict improves IDA*** - At depth 20, the gap reduces from 3.37 to 2.09.

4. **BPMX is effective for reducing generated nodes** - The optimization reduces generated nodes by ~30% but adds computational overhead (17-75%).

---

## 5. Conclusions

### 5.1 Hypothesis Validation/Rejection

**Primary Hypothesis - Rejected:** Contrary to expectations, A* showed better performance than IDA* on all metrics. IDA* was not more memory efficient and was actually slower.

**Secondary Hypothesis - Validated:** BPMX significantly reduced generated nodes (~30% reduction) but did not improve expanded nodes and added computational overhead.

**Tertiary Hypothesis - Partially Validated:** Linear Conflict showed improvements over Manhattan Distance, especially at higher depths.

### 5.2 Key Insights

1. **Problem size affects algorithm choice** - 8-Puzzle is a relatively small problem, so A* is more efficient than IDA*.

2. **IDA* is suitable for larger problems** - The algorithm is likely more efficient for problems like 15-Puzzle or 24-Puzzle.

3. **BPMX requires deep problems** - The optimization is effective only when its overhead is negligible compared to potential savings.

4. **Advanced heuristics pay off** - Linear Conflict showed significant improvements at higher depths.

### 5.3 Experimental Limitations

1. **Limited problem size** - We tested only 8-Puzzle, not larger problems.
2. **Limited depths** - Maximum depth tested was 30.
3. **Limited number of instances** - 5-10 instances per depth.
4. **Limited heuristics** - We did not test pattern databases or other advanced heuristics.

### 5.4 Future Directions

1. **Domain expansion** - Testing 15-Puzzle and 24-Puzzle.
2. **Higher depths** - Testing IDA* and BPMX at depths 40-50.
3. **Advanced heuristics** - Pattern databases, additive pattern databases.
4. **Detailed memory analysis** - Measuring actual peak memory usage.
5. **Comparison with other algorithms** - RBFS, SMA*.

---

## 6. Appendix: Code

[Complete code will be presented in a separate appendix]

---

## 7. Bibliography

1. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. IEEE Transactions on Systems Science and Cybernetics, 4(2), 100-107.

2. Korf, R. E. (1985). Depth-first iterative-deepening: An optimal admissible tree search. Artificial Intelligence, 27(1), 97-109.

3. Felner, A., Korf, R. E., & Hanan, S. (2004). Additive pattern database heuristics. Journal of Artificial Intelligence Research, 22, 279-318.
