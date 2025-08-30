#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, statistics, os
from pathlib import Path
from collections import defaultdict

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def load(files):
    rows = []
    for p in files:
        with open(p, newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append({
                    "file": Path(p).name,
                    "algo": (row.get("algorithm") or row.get("algo") or "").strip(),
                    "heur": (row.get("heuristic") or "").strip(),
                    "depth": _to_int(row.get("depth")),
                    "seed": _to_int(row.get("seed")),
                    "time": _to_float(row.get("time_sec") or row.get("time")),
                    "expanded": _to_int(row.get("expanded")),
                    "generated": _to_int(row.get("generated")),
                    "duplicates": _to_int(row.get("duplicates")),
                    "peak_open": _to_int(row.get("peak_open")),
                    "peak_closed": _to_int(row.get("peak_closed")),
                    "peak_recursion": _to_int(row.get("peak_recursion")),
                    "bound_final": _to_int(row.get("bound_final")),
                    "tie_break": (row.get("tie_break") or "").strip(),
                    "termination": (row.get("termination") or "ok").strip(),
                    "solvable": _to_int(row.get("solvable")) if row.get("solvable") not in (None, "") else 1,
                })
    # filter bad rows
    return [r for r in rows if r["algo"] and r["depth"] is not None and r["time"] is not None]

def mean_std(vals):
    if not vals: return (0.0, 0.0, 0)
    if len(vals) == 1: return (vals[0], 0.0, 1)
    return (statistics.mean(vals), statistics.pstdev(vals), len(vals))

def group_means(rows, by=("file","heur","algo","depth"), metrics=("time","expanded","generated")):
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = tuple(r[k] for k in by)
        for m in metrics:
            if r[m] is not None:
                agg[key][m].append(r[m])
    out = {}
    for k, m in agg.items():
        out[k] = {mm: mean_std(m[mm]) for mm in m.keys()}
    return out  # { (file,heur,algo,depth): {metric: (mean,std,n)} }

def crossover_table(means, file_name, heur):
    """Return [(depth, ratio)] for (IDA*/A*) where both exist."""
    # Collect depths with both algorithms for the given file+heur
    depths = sorted({k[3] for k in means if k[0]==file_name and k[1]==heur})
    table = []
    for d in depths:
        a = means.get((file_name, heur, "A*", d))
        i = means.get((file_name, heur, "IDA*", d))
        if a and i and a["time"][0] > 0:
            table.append((d, i["time"][0] / a["time"][0]))
    return table

def first_flip_crossing(table):
    """First depth where ratio crosses 1.0. Returns (depth, ratio, direction) or None."""
    if not table: return None
    table = sorted(table)
    prev_d, prev_r = table[0]
    for d, r in table[1:]:
        if prev_r > 1.0 and r <= 1.0: return (d, r, "down")  # IDA* becomes faster
        if prev_r <= 1.0 and r > 1.0: return (d, r, "up")    # A* becomes faster
        prev_d, prev_r = d, r
    return None

def bpmx_ratio(means, file_plain, file_bpmx):
    """Return depth->ratio for IDA*(BPMX)/IDA* where both files share depths."""
    depths = sorted({k[3] for k in means if (k[0]==file_plain or k[0]==file_bpmx) and k[2].startswith("IDA*")})
    out = []
    for d in depths:
        p = means.get((file_plain, "", "IDA*", d)) or means.get((file_plain, "manhattan", "IDA*", d)) or means.get((file_plain, "linear_conflict", "IDA*", d))
        b = means.get((file_bpmx, "", "IDA* (BPMX ON)", d)) or means.get((file_bpmx, "manhattan", "IDA* (BPMX ON)", d)) or means.get((file_bpmx, "linear_conflict", "IDA* (BPMX ON)", d))
        if p and b and p["time"][0] > 0:
            out.append((d, b["time"][0] / p["time"][0]))
    return sorted(out)

def write_summary_md(path: Path, rows, means):
    path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted({r["file"] for r in rows})
    heuristics = sorted({r["heur"] for r in rows if r["heur"]})

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Experiment Summary\n\n")
        f.write("This file was auto-generated from CSVs.\n\n")

        # Per-file summaries
        for fn in files:
            f.write(f"## {fn}\n\n")
            subs = [r for r in rows if r["file"] == fn and r["solvable"]==1 and r["termination"]=="ok"]
            if not subs:
                f.write("_No solvable-ok rows._\n\n"); continue
            algos = sorted({r["algo"] for r in subs})
            hs = sorted({r["heur"] for r in subs})

            for h in hs:
                f.write(f"### Heuristic: `{h or '—'}`\n\n")
                f.write("| depth | algo | time mean±std (s) | expanded mean | generated mean | n |\n")
                f.write("|---:|:---|---:|---:|---:|---:|\n")
                depths = sorted({r["depth"] for r in subs if r["heur"]==h})
                for d in depths:
                    for a in algos:
                        k = (fn, h, a, d)
                        m = means.get(k)
                        if not m: continue
                        tmu, tsd, tn = m["time"]; emu,_,_ = m["expanded"]; gmu,_,_ = m["generated"]
                        f.write(f"| {d} | {a} | {tmu:.6f}±{tsd:.6f} | {emu:.1f} | {gmu:.1f} | {tn} |\n")
                f.write("\n")

            # crossover (IDA*/A*) per heuristic
            for h in hs:
                table = crossover_table(means, fn, h)
                if not table: continue
                cross = first_flip_crossing(table)
                f.write(f"**Crossover (IDA*/A*) for `{h}`:** ")
                if cross:
                    f.write(f"first flip at depth **{cross[0]}** (ratio={cross[1]:.3f}, direction={cross[2]}).\n\n")
                else:
                    f.write("no flip within tested depths (ratios shown below).\n\n")
                f.write("| depth | ratio IDA*/A* |\n|---:|---:|\n")
                for d,r in sorted(table):
                    f.write(f"| {d} | {r:.3f} |\n")
                f.write("\n")

        # Unsolvable vs solvable (aggregate)
        f.write("## Solvable vs Unsolvable (aggregate across files)\n\n")
        by = defaultdict(lambda: defaultdict(list))  # (algo, solvable) -> metric -> vals
        for r in rows:
            key = (r["algo"], r["solvable"])
            by[key]["time"].append(r["time"])
            if r["expanded"] is not None: by[key]["expanded"].append(r["expanded"])
            if r["generated"] is not None: by[key]["generated"].append(r["generated"])
        f.write("| algo | solvable | time mean±std (s) | expanded mean | generated mean | n |\n")
        f.write("|:---|:---:|---:|---:|---:|---:|\n")
        for (a, sflag), m in sorted(by.items()):
            tmu, tsd, tn = mean_std(m["time"])
            emu = statistics.mean(m["expanded"]) if m["expanded"] else 0.0
            gmu = statistics.mean(m["generated"]) if m["generated"] else 0.0
            f.write(f"| {a} | {sflag} | {tmu:.6f}±{tsd:.6f} | {emu:.1f} | {gmu:.1f} | {tn} |\n")
        f.write("\n")

    print(f"Wrote {path}")

def main():
    ap = argparse.ArgumentParser(description="Summarize result CSVs and detect crossovers.")
    ap.add_argument("files", nargs="+", help="CSV files from runner.py")
    ap.add_argument("--out", default="report/summary.md")
    args = ap.parse_args()

    rows = load(args.files)
    means = group_means(rows)

    write_summary_md(Path(args.out), rows, means)

    # Console: tiny high-level
    print("\n== High-level checks ==")
    files = sorted({r["file"] for r in rows})
    for fn in files:
        hs = sorted({r["heur"] for r in rows if r["file"]==fn})
        for h in hs:
            table = crossover_table(means, fn, h)
            cross = first_flip_crossing(table) if table else None
            if table:
                print(f"{fn} [{h}]: ratios={[(d, round(r,3)) for d,r in table]}", end="")
                if cross:
                    print(f"  -> flip @ depth {cross[0]} ({cross[2]})")
                else:
                    print("  -> no flip in range")
    print()

if __name__ == "__main__":
    main()
