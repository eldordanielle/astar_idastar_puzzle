# Comparison between A* and IDA* on the 8-Puzzle Problem

Laboratory project for Artificial Intelligence Search course - Comprehensive comparison between A* and IDA* algorithms with various optimizations.

## 🎯 Project Objectives

Quantitative comparison between A* and IDA* algorithms on the 8-Puzzle problem, including:
- Comparison between Manhattan Distance and Linear Conflict heuristics
- Testing the impact of BPMX optimization on IDA*
- Performance analysis at different depths

## 📊 Key Results

**Surprising Insights:**
- A* showed better performance than IDA* on all metrics
- BPMX significantly reduced generated nodes (41% reduction)
- Linear Conflict improved IDA* performance at higher depths

## 🚀 Installation and Execution

### Environment Setup
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Running Experiments
```bash
# A* vs IDA* comparison with Manhattan
python -m src.experiments.runner --depths 10 15 20 --per_depth 10 --algo both --heuristic manhattan --out results/mani.csv

# A* vs IDA* comparison with Linear Conflict
python -m src.experiments.runner --depths 10 15 20 --per_depth 10 --algo both --heuristic linear --out results/astar_vs_ida_linear.csv

# BPMX testing at higher depths
python -m src.experiments.runner --depths 20 25 30 --per_depth 5 --algo ida --heuristic manhattan --bpmx --out results/ida_bpmx_deep.csv
```

### Creating Graphs
```bash
# Single plot
python -m src.experiments.plot results/mani.csv

# Comparative plot
python -m src.experiments.plot results/ida_plain_deep.csv results/ida_bpmx_deep.csv
```

### Statistical Analysis
```bash
python -m src.experiments.analyze
```

## 📁 Project Structure

```
astar_idastar_puzzle/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── report/                   # Laboratory report
│   ├── report.md            # Complete report
│   ├── outline.md           # Report outline
│   └── appendix.md          # Code appendix
├── results/                  # Experiment results
│   ├── mani.csv             # A* vs IDA* Manhattan
│   ├── astar_vs_ida_linear.csv
│   ├── ida_plain_deep.csv   # IDA* high depths
│   ├── ida_bpmx_deep.csv    # IDA* + BPMX
│   └── plots/               # Generated graphs
└── src/                     # Source code
    ├── domains/
    │   └── puzzle8.py       # 8-Puzzle implementation
    ├── heuristics/
    │   ├── manhattan.py     # Manhattan Distance
    │   └── linear_conflict.py # Linear Conflict
    ├── search/
    │   ├── a_star.py        # A* implementation
    │   └── ida_star.py      # IDA* + BPMX implementation
    └── experiments/
        ├── runner.py        # Experiment runner
        ├── plot.py          # Graph generation
        └── analyze.py       # Statistical analysis
```

## 📈 Detailed Results

### A* vs IDA* Comparison (Manhattan Distance)

| Depth | Algorithm | Expanded | Generated | Time (ms) |
|-------|-----------|----------|-----------|-----------|
| 10    | A*        | 13.6     | 25.8      | 0.07      |
| 10    | IDA*      | 15.6     | 25.2      | 0.05      |
| 15    | A*        | 54.6     | 95.6      | 0.24      |
| 15    | IDA*      | 96.0     | 161.8     | 0.28      |
| 20    | A*        | 75.8     | 129.2     | 0.38      |
| 20    | IDA*      | 255.6    | 430.2     | 0.72      |

### Linear Conflict Impact

Linear Conflict improved IDA* performance at depth 20:
- Expanded ratio: 2.09 (instead of 3.37)
- Generated ratio: 2.08 (instead of 3.33)

### BPMX Impact

BPMX showed significant improvement in generated nodes:
- Expanded ratio: 1.00 (no difference)
- Generated ratio: 0.59 (41% reduction!)
- Time ratio: 1.48-2.02 (BPMX slower)

## 🔬 Methodology

**Instance Generation:** The `scramble` function creates instances with known solution depth

**Performance Metrics:**
- Expanded Nodes - Number of nodes expanded
- Generated Nodes - Number of nodes generated  
- Time - Runtime in seconds
- Memory - Memory usage (peak_open, peak_closed)

**Test Depths:** 10, 15, 20 (and higher depths for BPMX testing)

## 📝 Key Conclusions

1. **A* outperforms IDA* on small problems** - 8-Puzzle is a relatively small problem
2. **The gap increases with depth** - At depth 20, IDA* expands 3.37x more nodes
3. **Linear Conflict improves IDA*** - Reduces the gap at higher depths
4. **BPMX is effective for reducing generated nodes** - 41% reduction but adds overhead

## 👨‍💻 Development

The project was developed in Python 3.x with:
- Full type hints
- Modular structure
- Comprehensive documentation
- Statistical analysis tools

## 📚 Bibliography

1. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths.
2. Korf, R. E. (1985). Depth-first iterative-deepening: An optimal admissible tree search.
3. Felner, A., Korf, R. E., & Hanan, S. (2004). Additive pattern database heuristics.
