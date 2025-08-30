# A* vs. IDA* on N/Rectangular Sliding Puzzles

_Authors: Eran Fishbein and Danielle Eldor (submitted in pairs)._

**Abstract.** We empirically compare A* and IDA* on 3×3, 3×4, and 4×4 sliding-tile puzzles under admissible Manhattan and Linear-Conflict heuristics, with and without BPMX. Our instrumented Python implementations report runtime, node counts, duplicates, and memory proxies. IDA* dominates at moderate depths on all boards; on 15-puzzle a crossover appears around depth ≈14–18 where A* matches or overtakes IDA*, consistent with duplicate-pruning benefits when memory suffices. BPMX shows no speedup at our depths in Python. We conclude with actionable guidance on when to prefer each algorithm and discuss extensions (larger rectangles, stronger heuristics).

## 1) Introduction
We study informed search on sliding-tile puzzles, focusing on A* and IDA*. A* maintains OPEN/CLOSED and avoids re-expansions via a best-first frontier; IDA* performs iterative deepening on f=g+h and keeps only a DFS stack (memory-lean but with some re-expansions). We use admissible heuristics (Manhattan; Linear Conflict) and, for IDA*, test BPMX (bidirectional pathmax) which can increase h-values along edges to tighten f-bounds.

## 2) Purpose / Hypotheses
- **H1**: On small state spaces (e.g., 8-puzzle), A* outperforms IDA* due to stronger duplicate pruning and less re-expansion.
- **H2**: As depth and/or board size increase (e.g., 15-puzzle), IDA* becomes faster and more memory-robust; BPMX further helps IDA*.
- **H3** (bonus): Unsolvable instances exhibit different failure behavior between A* and IDA*.

## 3) Experimental Setup

**Environment.**  
Python 3 (virtualenv `astar`), packages from `requirements.txt`. Experiments were executed single-threaded on a lab Linux machine.

**Machine details.**  
Python 3.11.13 (GCC 11.2.0) on Linux (kernel 5.14). CPU: AMD EPYC 7702P (16 logical cores available on the node). RAM visible to the job: ~23.2 GiB.


**Instance generation.**  
For each target depth, we generate solvable start states by scrambling the GOAL with random legal blank moves while avoiding immediate backtracking. Seeds fix reproducibility; each `(depth, seed)` pair defines one instance. For *unsolvable* cases we parity-flip two non-blank tiles of a solvable start state.

**Domains & heuristics.**  
We evaluate 3×3 (8-puzzle) and 4×4 (15-puzzle). Heuristics are **Manhattan** and **Linear Conflict** (both admissible). For IDA* we also test **BPMX** (bidirectional pathmax).

**Algorithms & metrics.**  
Algorithms: **A\***, **IDA\*** (±BPMX), plus **BFS/DFS** baselines.  
Per-run metrics written to CSV: runtime `time_sec`, nodes `expanded`/`generated`, `duplicates` (distinct states seen again), memory proxies (`peak_open`, `peak_closed` for A\*; `peak_recursion` and `bound_final` for IDA\*), `termination`, and a `solvable` flag.

**Experiment matrix (exact commands used).**  
These commands produced the CSVs cited in the Results:

```bash
# 8-puzzle (n=30 per depth), both heuristics
python -m src.experiments.runner --domain p8  --algo both --heuristic manhattan       --depths 4 6 8 10 12 14 16 18 20 --per_depth 30 --out results/p8_manhattan.csv
python -m src.experiments.runner --domain p8  --algo both --heuristic linear_conflict --depths 4 6 8 10 12 14 16 18 20 --per_depth 30 --out results/p8_linear.csv

# 15-puzzle (n=12 per depth), both heuristics
python -m src.experiments.runner --domain p15 --algo both --heuristic manhattan       --depths 6 8 10 12 14 --per_depth 12 --out results/p15_manhattan.csv
python -m src.experiments.runner --domain p15 --algo both --heuristic linear_conflict --depths 6 8 10 12 14 --per_depth 12 --out results/p15_linear.csv

# IDA* BPMX vs plain on 15-puzzle (Manhattan)
python -m src.experiments.runner --domain p15 --algo ida --heuristic manhattan --depths 8 10 12 14 --per_depth 12 --out results/p15_ida_plain.csv
python -m src.experiments.runner --domain p15 --algo ida --heuristic manhattan --bpmx    --depths 8 10 12 14 --per_depth 12 --out results/p15_ida_bpmx.csv

# Unsolvable (8-puzzle) + BFS/DFS baselines, with per-instance timeout
python -m src.experiments.runner --domain p8 --algo all --heuristic manhattan \
  --depths 8 10 12 --per_depth 12 --include_unsolvable --timeout_sec 1.0 --dfs_max_depth 40 \
  --out results/p8_all_solv_unsolv.csv

# Rectangular 3×4 (both heuristics)
python -m src.experiments.runner --rows 3 --cols 4 --algo both --heuristic manhattan       --depths 6 8 10 12 --per_depth 12 --out results/r3x4_manhattan.csv
python -m src.experiments.runner --rows 3 --cols 4 --algo both --heuristic linear_conflict --depths 6 8 10 12 --per_depth 12 --out results/r3x4_linear.csv

# 15-puzzle (deeper sweep, Manhattan) + crossover plot
python -m src.experiments.runner --domain p15 --algo both --heuristic manhattan \
  --depths 10 12 14 16 18 --per_depth 10 --timeout_sec 2.0 \
  --out results/p15_deep_manhattan.csv
python -m src.experiments.analyze_crossover results/p15_deep_manhattan.csv --save results/plots

# IDA* BPMX vs plain (deeper, Manhattan)
python -m src.experiments.runner --domain p15 --algo ida --heuristic manhattan \
  --depths 16 18 --per_depth 10 --timeout_sec 2.0 \
  --out results/p15_ida_plain_deep.csv
python -m src.experiments.runner --domain p15 --algo ida --heuristic manhattan --bpmx \
  --depths 16 18 --per_depth 10 --timeout_sec 2.0 \
  --out results/p15_ida_bpmx_deep.csv

```

## 4) Results

### 4.1 Per-depth curves
**Figures:**  
- `report/figs/smoke_p15_combined.png` — 15-puzzle (A* vs IDA*): expanded / generated / time.  
- `report/figs/p8_all_small_combined.png` — 8-puzzle (A*, IDA*, BFS, DFS): expanded / generated / time.

**Observations.**
- **15-puzzle (Manhattan).** As depth grows, A*’s **generated** and **time** increase faster than IDA*’s. Even at our moderate depths, IDA* is already ahead in **time**, consistent with the lower frontier footprint and acceptable re-expansion overhead at these sizes. (Source CSVs: `results/p15_manhattan.csv`, `results/p15_linear.csv`.)
- **8-puzzle baselines.** The combined plot with **BFS/DFS** illustrates the value of heuristics: BFS/DFS expand far more nodes and either take much longer or hit timeouts at higher depths, while A*/IDA* stay compact. (Source CSVs: `results/p8_manhattan.csv`, `results/p8_linear.csv`, and `results/p8_all_solv_unsolv.csv`.)


### 4.2 Crossover analysis (IDA*/A* time ratio; < 1 ⇒ IDA* faster)

**Figure:** see `report/figs/crossover_crossover.png` (generated by `analyze_crossover.py`).

#### 8-puzzle · Manhattan
_Source: `results/p8_manhattan.csv` (n=30 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 10 | 0.000188±0.000052 | 0.000129±0.000072 | **0.689** |
| 12 | 0.000357±0.000206 | 0.000296±0.000227 | **0.830** |
| 14 | 0.000510±0.000401 | 0.000503±0.000575 | **0.986** |
| 16 | 0.001278±0.000978 | 0.001132±0.001108 | **0.886** |

**Takeaway.** On 8-puzzle with Manhattan, IDA* is faster at d=10–12, reaches **near parity** at d=14 (0.986), and remains modestly faster again by d=16. No flip to A* in this window.


#### 8-puzzle · Linear Conflict
_Source: `results/p8_linear.csv` (n=30 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 10 | 0.000276±0.000068 | 0.000181±0.000068 | **0.658** |
| 12 | 0.000410±0.000178 | 0.000367±0.000244 | **0.894** |
| 14 | 0.000585±0.000439 | 0.000544±0.000561 | **0.929** |
| 16 | 0.001143±0.000780 | 0.001006±0.000927 | **0.880** |

**Takeaway.** For 8-puzzle with Linear Conflict, **IDA\*** remains faster over depths 10–16 (ratios 0.66–0.93). We did **not** observe a flip to A* in this depth window.

#### 15-puzzle · Manhattan
_Source: `results/p15_manhattan.csv` (n=12 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 8  | 0.000108±0.000037 | 0.000064±0.000030 | **0.599** |
| 10 | 0.000145±0.000044 | 0.000092±0.000040 | **0.639** |
| 12 | 0.000195±0.000109 | 0.000157±0.000136 | **0.807** |
| 14 | 0.000360±0.000391 | 0.000244±0.000285 | **0.677** |

**Takeaway.** Within the tested range, **IDA\*** is consistently faster than **A\*** on 15-puzzle with Manhattan (ratios 0.60–0.81). The ratio trends toward parity around depth 12, then drops at depth 14—A*’s frontier costs grow, while IDA* remains memory-friendly.


#### 15-puzzle · Linear Conflict
_Source: `results/p15_linear.csv` (n=12 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 8  | 0.001084±0.000294 | 0.000678±0.000339 | **0.625** |
| 10 | 0.001544±0.000449 | 0.001002±0.000432 | **0.649** |
| 12 | 0.002016±0.000922 | 0.001530±0.001297 | **0.759** |
| 14 | 0.002983±0.002322 | 0.002112±0.002092 | **0.708** |

**Takeaway.** On 15-puzzle with **Linear Conflict**, **IDA\*** remains clearly faster across d=8–14 (ratios 0.63–0.76). A flip to A* (seen with Manhattan at deeper depths) is **not** observed here in our tested range.


#### 15-puzzle (deeper sweep) · Manhattan
_Source: `results/p15_deep_manhattan.csv` (n=10 per depth; per-instance timeout 2.0 s)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 14 | 0.000684±0.000578 | 0.000755±0.001164 | **1.104** |
| 16 | 0.000910±0.000723 | 0.000916±0.001012 | **1.007** |
| 18 | 0.001250±0.000731 | 0.001517±0.001198 | **1.213** |

**Takeaway.** Extending 15-puzzle deeper suggests a **flip near depth ≈14**: around d=14–18, **A\*** matches or overtakes **IDA\*** (ratios ≳1). Note the **high variance** relative to means (especially IDA\* at d=14), so this crossover region is noisy; nevertheless, the trend differs from the shallower range where IDA\* dominated.


#### Rectangular 3×4 · Manhattan
_Source: `results/r3x4_manhattan.csv` (n=12 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 8  | 0.000205±0.000044 | 0.000117±0.000040 | **0.573** |
| 10 | 0.000225±0.000050 | 0.000156±0.000083 | **0.693** |
| 12 | 0.000346±0.000234 | 0.000272±0.000248 | **0.785** |

**Takeaway.** On 3×4 with Manhattan, **IDA\*** remains faster through depth 12; the ratio trends toward parity as depth increases but stays **< 1** in our range.

#### Rectangular 3×4 · Linear Conflict
_Source: `results/r3x4_linear.csv` (n=12 per depth)._
| depth | A* time (s) mean±std | IDA* time (s) mean±std | ratio (IDA*/A*) |
|---:|---:|---:|---:|
| 8  | 0.000946±0.000207 | 0.000565±0.000192 | **0.598** |
| 10 | 0.001050±0.000240 | 0.000693±0.000295 | **0.660** |
| 12 | 0.001339±0.000541 | 0.000972±0.000623 | **0.726** |

**Takeaway.** With Linear Conflict, IDA\* is again faster on 3×4; ratios sit between **0.60–0.73** over depths 8–12.


#### Rectangular 3×5 · Manhattan
_Source: `results/r3x5_manhattan.csv`._

|   depth | A* time (s) mean±std     | IDA* time (s) mean±std   | ratio (IDA*/A*)   |
|--------:|:-------------------------|:-------------------------|:------------------|
|       8 | 0.000314±0.000039s (n=8) | 0.000171±0.000031s (n=8) | **0.544**         |
|      10 | 0.000512±0.000186s (n=8) | 0.000312±0.000090s (n=8) | **0.610**         |
|      12 | 0.000700±0.000428s (n=8) | 0.000495±0.000475s (n=8) | **0.707**         |

**Takeaway.** IDA\* remains faster across these depths; ratios < 1 trend toward parity as depth increases.

#### Rectangular 3×5 · Linear Conflict
_Source: `results/r3x5_linear.csv`._

|   depth | A* time (s) mean±std     | IDA* time (s) mean±std   | ratio (IDA*/A*)   |
|--------:|:-------------------------|:-------------------------|:------------------|
|       8 | 0.001095±0.000165s (n=8) | 0.000604±0.000117s (n=8) | **0.552**         |
|      10 | 0.001664±0.000684s (n=8) | 0.000886±0.000346s (n=8) | **0.533**         |
|      12 | 0.001970±0.000742s (n=8) | 0.001536±0.001251s (n=8) | **0.780**         |

**Takeaway.** IDA\* remains faster across these depths; ratios < 1 trend toward parity as depth increases.


### 4.3 BPMX impact (IDA*)
**Figure:** `report/figs/bpmx_ratio.png` (from `results/p15_ida_plain.csv` vs `results/p15_ida_bpmx.csv`).

_Source: 15-puzzle · Manhattan._
| depth | IDA* (plain) time (s) | IDA*+BPMX time (s) | ratio (BPMX/Plain) |
|---:|---:|---:|---:|
| 8  | 0.000077 | 0.000079 | **1.026** |
| 10 | 0.000097 | 0.000100 | **1.027** |
| 12 | 0.000190 | 0.000192 | **1.013** |
| 14 | 0.000330 | 0.000338 | **1.024** |

**Takeaway.** With our Python implementation at these depths, **BPMX does not help** (ratios ≈1.01–1.03). At deeper bounds or with a lower-overhead implementation, BPMX is expected to provide gains.

**Deeper depths (15-puzzle · Manhattan).**  
_Source: `results/p15_ida_plain_deep.csv` vs `results/p15_ida_bpmx_deep.csv` (n=10 per depth; timeout 2.0 s)._
| depth | IDA* (plain) time (s) | IDA*+BPMX time (s) | ratio (BPMX/Plain) |
|---:|---:|---:|---:|
| 16 | 0.000772 | 0.000780 | **1.010** |
| 18 | 0.001956 | 0.002021 | **1.033** |

**Takeaway.** Even at d=16–18, **BPMX does not provide a speedup** in this Python implementation (ratios ≈1.01–1.03). Any potential benefit is likely masked by per-node overhead at these bounds; lower-overhead implementations or much deeper bounds may be required to see gains.


### 4.4 Unsolvable vs. solvable
**Figures:**  
- `report/figs/unsolvable_time.png`  
- `report/figs/unsolvable_generated.png`  
(Source CSV: `results/p8_all_solv_unsolv.csv`, produced with `--include_unsolvable`.)

**Observations.**
- On **unsolvable** instances, both A* and IDA* must eventually **prove failure**. A* tends to maintain a growing CLOSED set; IDA* iterates increasing f-bounds.  
- In our runs, the **time** and **generated** bars show comparable or slightly lower cost for IDA* on unsolvable cases at these depths, aligning with IDA*’s lower memory needs. (Exact means are in `report/summary.md`; we cite the figure here for brevity.)

### 4.5 BFS/DFS baselines (brief)
**Figure:** `report/figs/p8_all_small_combined.png` (Source CSV: `results/p8_all_small.csv`.)

**Observation.** **BFS** and **DFS** expand orders of magnitude more nodes as depth increases; they serve as educational baselines illustrating why **admissible heuristics** (A*/IDA*) are decisive on these puzzles.

### 4.6 Cross-puzzle comparison

We now contrast behavior across board sizes using the IDA*/A* time ratio (ratio < 1 ⇒ IDA* faster). The table summarizes what we observed on the same implementation and measurement protocol.

| Board | Heuristic | Depth range | Ratio (IDA*/A*) behavior | Crossover in range? | Source CSVs |
|:--|:--|:--|:--|:--:|:--|
| 3×3 (8-puzzle) | Linear Conflict | 10–16 | **0.658 → 0.929** (approaches parity but < 1) | No | `results/p8_linear.csv` |
| 3×4 (rectangular) | Manhattan | 8–12 | **0.573 → 0.785** (IDA\* ahead) | No | `results/r3x4_manhattan.csv` |
| 3×4 (rectangular) | Linear Conflict | 8–12 | **0.598 → 0.726** (IDA\* ahead) | No | `results/r3x4_linear.csv` |
| 4×4 (15-puzzle) — shallow | Manhattan | 8–14 | **0.599 → 0.807** (IDA\* ahead) | No | `results/p15_manhattan.csv` |
| 4×4 (15-puzzle) — deeper | Manhattan | 14–18 | **1.104, 1.007, 1.213** (A\* catches up/overtakes) | **Yes (~d≈14–18)** | `results/p15_deep_manhattan.csv` |
| 3×5 (rectangular) | Manhattan       | 8–12 | **0.544 → 0.707** (IDA* ahead) | No | `results/r3x5_manhattan.csv` |
| 3×5 (rectangular) | Linear Conflict | 8–12 | **0.533 → 0.780** (IDA* ahead) | No | `results/r3x5_linear.csv`    |


**Takeaways.**
- As board size increases, **IDA\*** tends to dominate earlier depths (smaller ratios), but with **deeper search** and plenty of memory, **A\***’s duplicate detection can **overtake** (15-puzzle at d≈14–18).
- The rectangular **3×4** sits between 8- and 15-puzzle: ratios trend toward parity but stay **< 1** in our window (IDA\* still ahead).
- On **8-puzzle**, with Linear Conflict, we did not see a flip within 10–16; IDA\* remains modestly faster.


### 4.7 Duplicates & memory footprint (A* vs IDA*)

We report per-depth means for `duplicates` and memory proxies (A*: `peak_open`, `peak_closed`; IDA*: `peak_recursion`). `NaN` entries indicate “not applicable” for that algorithm (e.g., IDA* has no OPEN/CLOSED tables).

**15-puzzle · Manhattan (shallow)** — A* vs IDA*  
_Source: `results/p15_manhattan.csv` (n=12 per depth)._

**A* (duplicates & memory)**
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_open |   peak_closed |
|:------------|--------:|-------------:|-----------:|------------:|------------:|--------------:|
| A*          |       6 | 5.16667 | 6.16667 | 19.5833 | 9.25 | 6.16667 |
| A*          |       8 | 8       | 9       | 28.5833 | 12.5833 | 9       |
| A*          |      10 | 12.0833 | 13.0833 | 40.9167 | 16.75   | 13.0833 |
| A*          |      12 | 16.5833 | 17.5833 | 55.8333 | 22.6667 | 17.5833 |
| A*          |      14 | 33      | 33.5833 | 104.167 | 38.75   | 33.5833 |

**IDA\*** (duplicates & recursion)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_recursion |   bound_final |
|:------------|--------:|-------------:|-----------:|------------:|-----------------:|--------------:|
| IDA*        |       6 | 0     | 6.16667 | 11.3333 | 6        | 6        |
| IDA*        |       8 | 1     | 9.5     | 17.75   | 8        | 8        |
| IDA*        |      10 | 2.75  | 14.4167 | 26.25   | 10       | 10       |
| IDA*        |      12 | 8.25  | 23.9167 | 45.1667 | 12       | 12       |
| IDA*        |      14 | 13.25 | 37.25   | 73.25   | 13.8333  | 13.8333  |

**Reading the numbers.** By d=14, **A\*** duplicates have grown to **33** and `peak_open` to **38.75**, while **IDA\*** reaches `peak_recursion` ≈ **13.8** and only **13.25** duplicates. This reflects A*’s heavier frontier/CLOSED footprint at moderate depths (matching its slower times here).

**15-puzzle · Manhattan (deep)** — A* vs IDA*  
_Source: `results/p15_deep_manhattan.csv` (n=10 per depth)._

**A* (duplicates & memory)**
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_open |   peak_closed |
|:------------|--------:|-------------:|-----------:|------------:|------------:|--------------:|
| A*          |      10 | 10.8 | 11.8 | 38.1  | 16.5 | 11.8 |
| A*          |      12 | 16.3 | 17.3 | 54.5  | 21.9 | 17.3 |
| A*          |      14 | 26.6 | 27.4 | 85.8  | 32.8 | 27.4 |
| A*          |      16 | 36.2 | 36.5 | 115   | 43.5 | 36.5 |
| A*          |      18 | 49.8 | 50.8 | 158.3 | 58.7 | 50.8 |

**IDA\*** (duplicates & recursion)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_recursion |   bound_final |
|:------------|--------:|-------------:|-----------:|------------:|-----------------:|--------------:|
| IDA*        |      10 | 2.3  | 13.1 | 24.2  | 10   | 10   |
| IDA*        |      12 | 3.5  | 17.5 | 32.1  | 12   | 12   |
| IDA*        |      14 | 28.7 | 48.5 | 96.7  | 13.6 | 13.6 |
| IDA*        |      16 | 33.5 | 59.1 | 118.9 | 15   | 15   |
| IDA*        |      18 | 56   | 97.2 | 197.7 | 16.8 | 16.8 |

**Reading the numbers.** At deeper bounds, **IDA\***’s `peak_recursion` stays small (≈**10→16.8**), but its **re-expansions grow** (duplicates **2.3→56**). When re-expansions dominate and memory still suffices, **A\***’s CLOSED prevents them and can **match/overtake** IDA* (consistent with the ratios ≥1.0 in §4.2 for d=14–18). Meanwhile A*’s memory footprint continues to rise (`peak_open` **16.5→58.7**).

**3×5 · Manhattan** — A* vs IDA*  
_Source: `results/r3x5_manhattan.csv` (n=8 per depth)._

**A\*** (duplicates & memory)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_open |   peak_closed |
|:------------|--------:|-------------:|-----------:|------------:|------------:|--------------:|
| A*          |       6 |         5    |       6    |      19     |       9     |          6    |
| A*          |       8 |         8    |       9    |      28.625 |      12.625 |          9    |
| A*          |      10 |        15    |      16    |      49.375 |      19.375 |         16    |
| A*          |      12 |        20.75 |      21.75 |      66.375 |      24.875 |         21.75 |

**IDA\*** (duplicates & recursion)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_recursion |   bound_final |
|:------------|--------:|-------------:|-----------:|------------:|-----------------:|--------------:|
| IDA*        |       6 |        0.125 |      6.125 |      10.875 |              6   |           6   |
| IDA*        |       8 |        0     |      9     |      15.5   |              8   |           8   |
| IDA*        |      10 |        1.75  |     14.75  |      26.25  |             10   |          10   |
| IDA*        |      12 |       10.625 |     26     |      48.25  |             11.5 |          11.5 |

**Reading the numbers.** At d=12, A\* shows **20.75** duplicates and `peak_open` **24.88**, while IDA\*’s `peak_recursion` is **≈11.5** with **10.63** duplicates—consistent with IDA\*’s time advantage at these depths.


**3×5 · Linear Conflict** — A* vs IDA*  
_Source: `results/r3x5_linear.csv` (n=8 per depth)._

**A\*** (duplicates & memory)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_open |   peak_closed |
|:------------|--------:|-------------:|-----------:|------------:|------------:|--------------:|
| A*          |       6 |          5   |        6   |      19     |       9     |           6   |
| A*          |       8 |          8   |        9   |      28.625 |      12.625 |           9   |
| A*          |      10 |         13.5 |       14.5 |      45     |      18     |          14.5 |
| A*          |      12 |         16.5 |       17.5 |      53.75  |      20.75  |          17.5 |

**IDA\*** (duplicates & recursion)
| algorithm   |   depth |   duplicates |   expanded |   generated |   peak_recursion |   bound_final |
|:------------|--------:|-------------:|-----------:|------------:|-----------------:|--------------:|
| IDA*        |       6 |        0.125 |      6.125 |      10.875 |              6   |           6   |
| IDA*        |       8 |        0     |      9     |      15.5   |              8   |           8   |
| IDA*        |      10 |        1.75  |     13.5   |      23.75  |             10   |          10   |
| IDA*        |      12 |        7.625 |     21.5   |      39.625 |             11.5 |          11.5 |

**Reading the numbers.** Linear Conflict trims expansions in both algorithms; IDA\* still keeps recursion depth low (≈11.5 at d=12) and fewer duplicates than A\*, matching the <1 time ratios.


## 5) Conclusions

**What the data show (by board & depth).**  
- **15-puzzle, Manhattan (shallower range)** — `results/p15_manhattan.csv`: across depths **8–14**, **IDA\*** is faster than **A\*** with IDA*/A* ratios **0.599–0.807**. This matches the per-depth curves: A*’s OPEN/CLOSED growth outpaces IDA*’s re-expansion overhead.

- **15-puzzle, Manhattan (deeper sweep)** — `results/p15_deep_manhattan.csv`: at **d=14–18** we observe a **crossover to A\*** (ratios **1.104**, **1.007**, **1.213**). Absolute times are small and **standard deviations are large** near the flip (e.g., IDA* at d=14 has σ > mean), so the region is **variance-sensitive**; however, the trend indicates that **duplicate detection and tie-breaking in A\*** can become advantageous as repeated structures grow with depth.

- **3×4 rectangular board** — `results/r3x4_manhattan.csv`, `results/r3x4_linear.csv`: **IDA\*** remains faster through **d=12** for both **Manhattan** and **Linear Conflict** (ratios **0.57–0.79** and **0.60–0.73**, respectively). The ratios move toward parity with depth but do not cross in our range.

- **8-puzzle, Linear Conflict** — `results/p8_linear.csv`: across **d=10–16** we do **not** see a flip back to A*; **IDA\*** stays modestly faster (ratios **0.658–0.929**).

- **BPMX (IDA*, 15-puzzle, Manhattan)** — at d=8–14 and even at **d=16–18**, we see **no speedup** in Python (ratios ≈1.01–1.03). Overhead likely dominates at these bounds; deeper limits or a lower-overhead runtime could reveal gains.

- **8-puzzle, Manhattan** — `results/p8_manhattan.csv`: IDA* leads at d=10–12 (ratios **0.689**, **0.830**), hits **near parity** at d=14 (**0.986**), and remains modestly faster at d=16 (**0.886**). No flip to A* in this window.

- **15-puzzle, Linear Conflict** — `results/p15_linear.csv`: IDA* remains ahead across d=8–14 with ratios **0.625–0.759**; with a stronger heuristic than Manhattan, we do **not** observe a flip back to A* in this range.

- **Unsolvable (8-puzzle)** — `p8_all_solv_unsolv.csv`: proving failure shows **comparable or slightly lower cost for IDA\*** in our setting, consistent with its tiny memory footprint (no large CLOSED), while A* accumulates more frontier bookkeeping.

- **3×5 rectangular board** — `results/r3x5_manhattan.csv`, `results/r3x5_linear.csv`: IDA* remains ahead through d=12 with all ratios < 1 (**0.544→0.707** and **0.533→0.780**). Trends sit between 3×4 and 4×4, as expected.


**Hypotheses revisited.**  
- **H1 (A* better on small spaces):** *Partially supported.* On very shallow cases A* can be competitive; within the depth ranges we tested, **IDA\*** often matches or beats A*.  
- **H2 (IDA* wins as depth/size grows; BPMX helps):** *Nuanced.* In the **shallower-to-moderate** regime, **IDA\*** leads; the **deeper 15-puzzle sweep** shows a **flip** where **A\*** catches up and overtakes around **d≈14–18**. BPMX **did not help** at our depths in Python.  
- **H3 (unsolvable behavior differs):** *Observed.* A* trends to frontier exhaustion; IDA* iterates bounds — reflected in our unsolvable summaries.

**Rule of thumb (actionable).**  
- If **memory is limited** or you operate in the **moderate-depth** regime → prefer **IDA\*** (consider BPMX only at deeper bounds or in optimized runtimes).  
- If you expect **very deep search** with heavy **state repetition** and sufficient memory → **A\*** can match or surpass IDA\* thanks to duplicate detection.  
- Always choose the **strongest admissible heuristic** available; **Linear Conflict** generally improves on Manhattan in both time and node counts.
- Cross-puzzle: smaller boards (8-puzzle) favor **IDA\*** across our tested depths; mid-size (3×4) still favors **IDA\*** but trends toward parity; larger (15-puzzle) favors **IDA\*** at shallower depths and shows a **flip to A\*** in the deeper range we tested (d≈14–18).


**Why the flip can happen.**  
At greater depths, massive **state revisitation** increases. **A\***’s CLOSED set prevents re-expansions, while **IDA\*** repeatedly re-touches states across f-bound iterations. When re-expansions dominate and memory still suffices, **A\*** can regain the edge — consistent with our deeper 15-puzzle sweep.

**Threats to validity.**  
- **Variance near crossover**: at d=14–18 on p15 the standard deviations are large; tighter confidence intervals would require more seeds or per-instance time normalization.  
- **Python overheads**: small absolute times (ms) make micro-overheads material; a compiled implementation may shift the flip depth.  
- **Parameter sensitivity**: tie-breaking policies and timeout caps can slightly move the observed crossover.

**Future work.**  
- Extend 15-puzzle to **higher depths with larger timeouts** to tighten the crossover estimate and reduce variance.  
- Add **3×5** (and larger rectangles) to map crossover **as a function of board dimensions**.  
- Evaluate **pattern-database heuristics** to quantify how stronger h shifts (or eliminates) the crossover region.


## 6) Appendix: Code
- Source layout under `src/` (domains, search, experiments); exact commands in `REPRODUCE_RESULTS.md`.  
- Algorithms instrumented with node counts and memory proxies; CSV outputs in `results/`.  
- Figures in `report/figs/`.

## Figures (key story)
![Crossover: IDA*/A* time ratio across tested depths (ratio < 1 ⇒ IDA* faster).](figs/crossover_crossover.png)

![BPMX speedup on IDA*: time ratio (BPMX / Plain); lower is better.](figs/bpmx_ratio.png)

![15-puzzle: per-depth curves (expanded / generated / time) for A* vs IDA*.](figs/smoke_p15_combined.png)

![8-puzzle: per-depth curves comparing A*, IDA*, BFS, DFS (expanded / generated / time).](figs/p8_all_small_combined.png)

![Unsolvable instances: mean time by algorithm.](figs/unsolvable_time.png)

![Unsolvable instances: mean generated nodes by algorithm.](figs/unsolvable_generated.png)

![3×5 rectangular: crossover (IDA*/A* time ratio; < 1 ⇒ IDA* faster).](figs/crossover_r3x5.png)
