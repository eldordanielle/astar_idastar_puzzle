#!/usr/bin/env python3
import argparse, csv, statistics, math
from collections import defaultdict
from pathlib import Path
import os
import matplotlib
if "MPLBACKEND" not in os.environ:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Okabe–Ito palette (CVD-friendly)
COLORS = {"plain": "#0072B2", "bpmx": "#D55E00"}  # blue vs vermillion
GRAY = "#7F7F7F"

def _get(row, keys, default=None):
    for k in keys:
        if k in row and row[k] != "":
            return row[k]
    return default

def _to_int(x):
    try: return int(x)
    except: return None

def _to_float(x):
    try: return float(x)
    except: return None

def load_ok(path):
    """Read CSV, keep only rows with termination ∈ {ok, ''}."""
    out = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            term = (_get(row, ["termination", "status"], "") or "").lower().strip()
            if term not in ("", "ok"):
                continue
            algo = _get(row, ["algorithm", "algo"], "")
            depth = _to_int(_get(row, ["depth"]))
            expanded = _to_int(_get(row, ["expanded"]))
            generated = _to_int(_get(row, ["generated"]))
            time_sec = _to_float(_get(row, ["time_sec", "time"]))
            if algo and depth is not None:
                out.append({"algo": algo, "depth": depth,
                            "expanded": expanded, "generated": generated, "time_sec": time_sec})
    return out

def autodetect_label(rows, preferred, fallback="IDA*"):
    labels = {r["algo"] for r in rows}
    if preferred in labels: return preferred
    if fallback  in labels: return fallback
    # last resort: any IDA-ish string
    for lab in labels:
        if "ida" in lab.lower():
            return lab
    return preferred

def group(rows, label):
    g = defaultdict(list)
    for r in rows:
        if r["algo"] == label and r["depth"] is not None:
            g[r["depth"]].append(r)
    return g  # depth -> list[rows]

def mean_sem(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    if len(vals) == 1:
        return float(vals[0]), 0.0
    m = statistics.mean(vals)
    sd = statistics.pstdev(vals) if len(vals) == 1 else statistics.stdev(vals)
    sem = sd / math.sqrt(len(vals))
    return float(m), float(sem)

def ratio_sem(b_mean, b_sem, p_mean, p_sem):
    """SEM of ratio r = B/P via error propagation."""
    if b_mean is None or p_mean in (None, 0):
        return math.nan
    r = b_mean / p_mean
    # guard against zero division
    if b_mean == 0 or p_mean == 0:
        return math.nan
    with math.errstate if hasattr(math, "errstate") else dummy():
        try:
            term = (b_sem / b_mean) ** 2 + (p_sem / p_mean) ** 2
            return abs(r) * math.sqrt(term)
        except Exception:
            return math.nan

class dummy:
    def __enter__(self): return self
    def __exit__(self, *a): return False

def analyze(plain_csv, bpmx_csv, label_plain="IDA*", label_bpmx="IDA* (BPMX ON)",
            dmin=4, dmax=20, out_csv=None, out_png=None, show_err=True):
    plain = load_ok(plain_csv)
    bpmx  = load_ok(bpmx_csv)

    label_plain = autodetect_label(plain, label_plain, "IDA*")
    label_bpmx  = autodetect_label(bpmx,  label_bpmx,  "IDA*")

    P = group(plain, label_plain)
    B = group(bpmx,  label_bpmx)

    depths = sorted(d for d in set(P) & set(B) if (dmin is None or d >= dmin) and (dmax is None or d <= dmax))
    if not depths:
        print("No common depths between files after filtering.")
        return

    rows_out = []
    print("\nDepth  nP nB |  Exp(mean)  B/P  |  Gen(mean)  B/P  |  Time(s)   B/P")
    print("-"*74)
    for d in depths:
        p_rows, b_rows = P[d], B[d]
        p_exp_m, p_exp_s = mean_sem([r["expanded"] for r in p_rows])
        b_exp_m, b_exp_s = mean_sem([r["expanded"] for r in b_rows])
        p_gen_m, p_gen_s = mean_sem([r["generated"] for r in p_rows])
        b_gen_m, b_gen_s = mean_sem([r["generated"] for r in b_rows])
        p_tim_m, p_tim_s = mean_sem([r["time_sec"]  for r in p_rows])
        b_tim_m, b_tim_s = mean_sem([r["time_sec"]  for r in b_rows])

        r_exp = (b_exp_m / p_exp_m) if p_exp_m not in (None, 0) and b_exp_m is not None else math.nan
        r_gen = (b_gen_m / p_gen_m) if p_gen_m not in (None, 0) and b_gen_m is not None else math.nan
        r_tim = (b_tim_m / p_tim_m) if p_tim_m not in (None, 0) and b_tim_m is not None else math.nan

        rows_out.append({
            "depth": d, "n_plain": len(p_rows), "n_bpmx": len(b_rows),
            "exp_plain_mean": p_exp_m, "exp_bpmx_mean": b_exp_m, "exp_ratio": r_exp,
            "gen_plain_mean": p_gen_m, "gen_bpmx_mean": b_gen_m, "gen_ratio": r_gen,
            "time_plain_mean": p_tim_m, "time_bpmx_mean": b_tim_m, "time_ratio": r_tim,
            "time_ratio_sem": ratio_sem(b_tim_m, b_tim_s, p_tim_m, p_tim_s),
        })

        print(f"{d:>5} {len(p_rows):>3} {len(b_rows):>3} | "
              f"{(p_exp_m or 0):9.1f} {r_exp:5.2f} | "
              f"{(p_gen_m or 0):9.1f} {r_gen:5.2f} | "
              f"{(p_tim_m or 0):8.4f} {r_tim:5.2f}")

    # Optional CSV dump
    if out_csv:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            w.writeheader(); w.writerows(rows_out)
        print(f"\nSaved per-depth summary -> {out_csv}")

    # Optional plot
    if out_png:
        xs = [r["depth"] for r in rows_out]
        ys = [r["time_ratio"] for r in rows_out]
        es = [r["time_ratio_sem"] for r in rows_out]
        plt.figure(figsize=(7.8, 4.8))
        if show_err and all(e is not None and not math.isnan(e) for e in es):
            plt.errorbar(xs, ys, yerr=es, capsize=3, lw=2.0, marker="o", color=COLORS["bpmx"])
        else:
            plt.plot(xs, ys, lw=2.0, marker="o", color=COLORS["bpmx"])
        plt.axhline(1.0, color=GRAY, linestyle=":")
        plt.xlabel("Depth"); plt.ylabel("Time ratio  (BPMX / plain)")
        plt.title("IDA* + BPMX vs IDA*  (lower is better)")
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout(); plt.savefig(out_png, dpi=200); plt.close()
        print(f"Saved plot -> {out_png}")

def main():
    ap = argparse.ArgumentParser(description="Analyze BPMX impact (IDA*+BPMX vs IDA*)")
    ap.add_argument("--plain", required=True, help="CSV with IDA* (plain)")
    ap.add_argument("--bpmx",  required=True, help="CSV with IDA* (BPMX ON)")
    ap.add_argument("--label_plain", default="IDA*", help="Algorithm label for plain (if needed)")
    ap.add_argument("--label_bpmx",  default="IDA* (BPMX ON)", help="Algorithm label for BPMX (if needed)")
    ap.add_argument("--dmin", type=int, default=4)
    ap.add_argument("--dmax", type=int, default=20)
    ap.add_argument("--out_csv", default=None)
    ap.add_argument("--out_png", default="results/plots/bpmx_ratio.png")
    ap.add_argument("--no_err", action="store_true", help="Hide error bars")
    args = ap.parse_args()
    analyze(args.plain, args.bpmx, args.label_plain, args.label_bpmx,
            args.dmin, args.dmax, args.out_csv, args.out_png, show_err=not args.no_err)

if __name__ == "__main__":
    main()
