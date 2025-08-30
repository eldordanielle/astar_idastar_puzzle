#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, statistics
from pathlib import Path
from collections import defaultdict

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def load_one(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            algo = (row.get("algorithm") or row.get("algo") or "").strip()
            depth = _to_int(row.get("depth"))
            heur  = (row.get("heuristic") or "").strip()
            t     = _to_float(row.get("time_sec") or row.get("time"))
            expd  = _to_int(row.get("expanded"))
            gen   = _to_int(row.get("generated"))
            term  = (row.get("termination") or "ok").strip()
            if algo and depth is not None and t is not None:
                rows.append({"algo":algo,"depth":depth,"heur":heur,"time":t,"expanded":expd,"generated":gen,"termination":term})
    return rows

def mean(vals): 
    return (statistics.mean(vals), 0.0 if len(vals)==1 else statistics.pstdev(vals), len(vals))

def means_by_algo_depth(rows, only_ok=True, heur_filter=None):
    agg = defaultdict(lambda: defaultdict(list))  # (algo, depth) -> metric -> vals
    for r in rows:
        if only_ok and r["termination"] != "ok": 
            continue
        if heur_filter and r["heur"] != heur_filter:
            continue
        k = (r["algo"], r["depth"])
        for m in ("time","expanded","generated"):
            if r[m] is not None:
                agg[k][m].append(r[m])
    out = {}
    for k,m in agg.items():
        out[k] = {mm: mean(m[mm]) for mm in m}
    return out

def print_claims(csv_path, depths, heuristic=None):
    rows = load_one(csv_path)
    means = means_by_algo_depth(rows, only_ok=True, heur_filter=heuristic)
    p = Path(csv_path).name
    print(f"# Claims from {p}" + (f" (heuristic={heuristic})" if heuristic else ""))
    for d in depths:
        a = means.get(("A*", d)); i = means.get(("IDA*", d))
        if not a or not i: 
            print(f"- depth {d}: insufficient data"); 
            continue
        a_mu,a_sd,a_n = a["time"]; i_mu,i_sd,i_n = i["time"]
        ratio = i_mu / a_mu if a_mu > 0 else float("inf")
        print(f"- depth {d}: A* {a_mu:.6f}±{a_sd:.6f}s (n={a_n}); "
              f"IDA* {i_mu:.6f}±{i_sd:.6f}s (n={i_n}); "
              f"ratio IDA*/A* = **{ratio:.3f}**  ← source: `{p}`")

def print_bpmx(plain_csv, bpmx_csv, depths, heuristic=None):
    rp = load_one(plain_csv); rb = load_one(bpmx_csv)
    mp = means_by_algo_depth(rp, heur_filter=heuristic); mb = means_by_algo_depth(rb, heur_filter=heuristic)
    p = Path(plain_csv).name; b = Path(bpmx_csv).name
    print(f"# BPMX from {p} vs {b}" + (f" (heuristic={heuristic})" if heuristic else ""))
    for d in depths:
        p_ida = mp.get(("IDA*", d)); b_ida = mb.get(("IDA* (BPMX ON)", d))
        if not p_ida or not b_ida:
            print(f"- depth {d}: insufficient data"); 
            continue
        pr, br = p_ida["time"][0], b_ida["time"][0]
        ratio = br / pr if pr > 0 else float("inf")
        print(f"- depth {d}: IDA* {pr:.6f}s → BPMX {br:.6f}s; ratio BPMX/Plain = **{ratio:.3f}**  ← sources: `{p}`, `{b}`")

def main():
    ap = argparse.ArgumentParser(description="Print citable claims with their CSV sources.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c1 = sub.add_parser("crossover", help="A* vs IDA* means and ratio by depth")
    c1.add_argument("--file", required=True)
    c1.add_argument("--depths", type=int, nargs="+", required=True)
    c1.add_argument("--heuristic", default=None)

    c2 = sub.add_parser("bpmx", help="IDA* vs IDA*+BPMX ratio by depth")
    c2.add_argument("--plain", required=True)
    c2.add_argument("--bpmx", required=True)
    c2.add_argument("--depths", type=int, nargs="+", required=True)
    c2.add_argument("--heuristic", default=None)

    args = ap.parse_args()
    if args.cmd == "crossover":
        print_claims(args.file, args.depths, heuristic=args.heuristic)
    else:
        print_bpmx(args.plain, args.bpmx, args.depths, heuristic=args.heuristic)

if __name__ == "__main__":
    main()
