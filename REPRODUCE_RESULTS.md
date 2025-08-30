# How to Reproduce Experimental Results

This guide explains how to reproduce all the experimental results from scratch.

## Prerequisites

1. Python 3.8 or higher
2. Virtual environment capability
3. Required packages (see requirements.txt)

## Step-by-Step Reproduction

### 1. Setup Environment

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On Linux/Mac

# Install requirements
pip install -r requirements.txt
```

### 2. Run All Experiments

```bash
# Run the comprehensive experiment script
python run_experiments.py
```

This will:
- Run A* and IDA* experiments with Manhattan heuristic
- Run A* and IDA* experiments with Linear Conflict heuristic
- Run IDA* with BPMX optimization
- Generate all plots automatically

### 3. Alternative: Run Individual Experiments

If you prefer to run experiments individually:

```bash
# Manhattan heuristic experiments
python -m src.experiments.enhanced_runner --depths 5 10 15 20 --per_depth 10 --heuristic manhattan --algo both --out results/manhattan.csv

# Linear Conflict heuristic experiments
python -m src.experiments.enhanced_runner --depths 5 10 15 20 --per_depth 10 --heuristic linear_conflict --algo both --out results/linear_conflict.csv

# IDA* with BPMX
python -m src.experiments.enhanced_runner --depths 5 10 15 20 --per_depth 10 --heuristic manhattan --algo ida --bpmx --out results/ida_bpmx.csv
```

### 4. Generate Plots

```bash
# Individual plots
python -m src.experiments.plot results/manhattan.csv
python -m src.experiments.plot results/linear_conflict.csv

# Combined plots
python -m src.experiments.plot results/manhattan.csv results/linear_conflict.csv
python -m src.experiments.plot results/manhattan.csv results/ida_bpmx.csv
```

### 5. Analyze Results

```bash
# General analysis
python analyze_results.py

# BPMX-specific analysis
python analyze_bpmx.py
```

## Expected Output

### Files Generated

- `results/manhattan.csv` - A* and IDA* with Manhattan heuristic
- `results/linear_conflict.csv` - A* and IDA* with Linear Conflict heuristic  
- `results/ida_bpmx.csv` - IDA* with BPMX optimization
- `results/plots/*.png` - All visualization plots

### Key Findings

1. **A* vs IDA***: A* outperforms IDA* on all metrics for 8-puzzle
2. **Heuristics**: Linear Conflict significantly improves performance over Manhattan
3. **BPMX**: Reduces generated nodes by ~30% but adds computational overhead

## Troubleshooting

- Ensure virtual environment is activated
- Check Python version compatibility
- Verify all dependencies are installed
- On Windows, use backslashes in paths

## Results Verification

The final results should match the patterns shown in the report:
- A* faster than IDA* at all depths
- Linear Conflict better than Manhattan
- BPMX reduces generated nodes but increases time
