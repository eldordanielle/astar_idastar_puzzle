import csv
import statistics
from collections import defaultdict
from pathlib import Path

def _norm(row, keys, default=""):
    for k in keys:
        if k in row and row[k] not in ("", None):
            return row[k]
    return default

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def analyze_csv(file_path):
    """Statistical analysis tolerant to both 'algo' and 'algorithm' schemas."""
    by = defaultdict(lambda: defaultdict(list))
    with open(file_path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = _norm(row, ["algorithm", "algo"])
            depth = _to_int(_norm(row, ["depth"]))
            if not algo or depth is None:
                continue
            k = f"{algo}_{depth}"
            expanded = _to_int(_norm(row, ["expanded"]))
            generated = _to_int(_norm(row, ["generated"]))
            time_sec = _to_float(_norm(row, ["time_sec", "time"]))
            peak_open = _to_int(_norm(row, ["peak_open"]))
            peak_closed = _to_int(_norm(row, ["peak_closed"]))

            if expanded is not None: by[k]["expanded"].append(expanded)
            if generated is not None: by[k]["generated"].append(generated)
            if time_sec is not None:  by[k]["time"].append(time_sec)
            if peak_open is not None: by[k]["peak_open"].append(peak_open)
            if peak_closed is not None: by[k]["peak_closed"].append(peak_closed)

    stats = {}
    for k, vals in by.items():
        stats[k] = {}
        for m, arr in vals.items():
            if arr:
                stats[k][m] = {
                    "mean": statistics.mean(arr),
                    "median": statistics.median(arr),
                    "min": min(arr),
                    "max": max(arr),
                    "std": statistics.stdev(arr) if len(arr) > 1 else 0.0,
                }
    return stats

def _print_table_row(metric, a, i):
    a_val = a.get(metric, {}).get("mean")
    i_val = i.get(metric, {}).get("mean")
    if a_val is None or i_val is None:
        return
    ratio = (i_val / a_val) if a_val > 0 else float("inf")
    print(f"{metric:<15} {a_val:<15.2f} {i_val:<15.2f} {ratio:<15.2f}")

def print_comparison(stats, depths=(10, 15, 20)):
    print("=" * 80)
    print("Comparison between A* and IDA*")
    print("=" * 80)
    for d in depths:
        akey = f"A*_{d}"
        ikey = f"IDA*_{d}"
        if akey in stats and ikey in stats:
            print(f"\nDepth {d}:")
            print("-" * 60)
            print(f"{'Metric':<15} {'A* (avg)':<15} {'IDA* (avg)':<15} {'Ratio (IDA*/A*)':<15}")
            for m in ("expanded", "generated", "time"):
                _print_table_row(m, stats[akey], stats[ikey])

def print_bpmx_analysis(stats_plain, stats_bpmx, depths=(20, 25, 30)):
    print("\n" + "=" * 80)
    print("Analysis of BPMX impact on IDA*")
    print("=" * 80)
    for d in depths:
        pkey = f"IDA*_{d}"
        bkey = f"IDA* (BPMX ON)_{d}"
        if pkey in stats_plain and bkey in stats_bpmx:
            print(f"\nDepth {d}:")
            print("-" * 60)
            print(f"{'Metric':<15} {'IDA* Plain':<15} {'IDA* + BPMX':<15} {'Ratio (BPMX/Plain)':<15}")
            for m in ("expanded", "generated", "time"):
                p = stats_plain[pkey].get(m, {}).get("mean")
                b = stats_bpmx[bkey].get(m, {}).get("mean")
                if p is None or b is None: 
                    continue
                ratio = (b / p) if p > 0 else float("inf")
                print(f"{m:<15} {p:<15.2f} {b:<15.2f} {ratio:<15.2f}")

def main():
    files = {
        "Manhattan": "results/mani.csv",
        "Linear Conflict": "results/astar_vs_ida_linear.csv",
        "IDA* Plain Deep": "results/ida_plain_deep.csv",
        "IDA* BPMX Deep": "results/ida_bpmx_deep_fixed2.csv",
    }
    all_stats = {}
    for name, path in files.items():
        if Path(path).exists():
            print(f"\nAnalyzing {name}...")
            all_stats[name] = analyze_csv(path)

    if "Manhattan" in all_stats:
        print_comparison(all_stats["Manhattan"])
    if "Linear Conflict" in all_stats:
        print("\n" + "=" * 80)
        print("Comparison with Linear Conflict")
        print_comparison(all_stats["Linear Conflict"])
    if "IDA* Plain Deep" in all_stats and "IDA* BPMX Deep" in all_stats:
        print_bpmx_analysis(all_stats["IDA* Plain Deep"], all_stats["IDA* BPMX Deep"])

if __name__ == "__main__":
    main()
