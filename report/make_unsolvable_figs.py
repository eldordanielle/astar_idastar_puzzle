# report/make_unsolvable_figs_v2.py
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

CSV = Path("results/p8_all_solv_unsolv.csv")
OUT = Path("report/figs/p8_unsolv_vs_solv_combo.png")
OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)

# Keep just A* and IDA* for clarity
df = df[df["algorithm"].isin(["A*", "IDA*"])].copy()

# If all unsolvables timed out, time_sec will already be ~timeout cap (e.g., 1.0s).
# Still, detect the cap robustly.
timeout_like = df.loc[df["termination"]=="timeout", "time_sec"]
TIMEOUT_CAP = float(timeout_like.median()) if not timeout_like.empty else 1.0

# “Adjusted” time: if timeout, count as TIMEOUT_CAP; else use measured time
df["time_adj"] = np.where(df["termination"]=="timeout", TIMEOUT_CAP, df["time_sec"])

# Split groups
sol = df[df["solvable"]==1]
uns = df[df["solvable"]==0]

def agg_time_genn(rows):
    g = (rows.groupby("algorithm")
              .agg(time_mean=("time_adj","mean"),
                   time_std =("time_adj","std"),
                   gen_mean =("generated","mean"),
                   gen_std  =("generated","std"),
                   n=("algorithm","size"))
              .reindex(["A*","IDA*"]))
    # Avoid NaN std bars when n==1
    g["time_std"] = g["time_std"].fillna(0.0)
    g["gen_std"]  = g["gen_std"].fillna(0.0)
    return g

S = agg_time_genn(sol)
U = agg_time_genn(uns)

# Timeout rates for annotation
def timeout_rate(rows):
    if rows.empty: return None
    m = (rows["termination"]=="timeout").mean()
    return 100.0*float(m)

tmo_A = timeout_rate(uns[uns["algorithm"]=="A*"])
tmo_I = timeout_rate(uns[uns["algorithm"]=="IDA*"])

algos = ["A*","IDA*"]
x = np.arange(len(algos))
w = 0.38

fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,4.2))
fig.suptitle("8-puzzle · Manhattan — Solvable vs Unsolvable", y=1.02, fontsize=16)

# Left: time (log)
ax1.bar(x - w/2, S["time_mean"], yerr=S["time_std"], width=w, label="Solvable", capsize=3)
ax1.bar(x + w/2, U["time_mean"], yerr=U["time_std"], width=w, label="Unsolvable", capsize=3)
ax1.set_yscale("log")
ax1.set_xticks(x, algos)
ax1.set_ylabel("seconds (log scale)")
ax1.set_title("Mean time per run (log scale)")
ax1.legend(loc="upper left")

# Annotate unsolvable timeout rates above orange bars (if we have them)
ylim = ax1.get_ylim()
for i,(rate,mean) in enumerate([(tmo_A,U.loc["A*","time_mean"]),
                                (tmo_I,U.loc["IDA*","time_mean"])]):
    if np.isfinite(mean) and mean>0:
        y = min(mean*2.0, ylim[1]/1.3)  # place safely below the top
        label = "unsolv timeout: " + ("N/A" if rate is None else f"{rate:.0f}%")
        ax1.annotate(label, xy=(x[i]+w/2, mean), xytext=(0,5),
                     textcoords="offset points", ha="center", fontsize=9)

# Right: generated nodes (log)
ax2.bar(x - w/2, S["gen_mean"], yerr=S["gen_std"], width=w, label="Solvable", capsize=3)
ax2.bar(x + w/2, U["gen_mean"], yerr=U["gen_std"], width=w, label="Unsolvable", capsize=3)
ax2.set_yscale("log")
ax2.set_xticks(x, algos)
ax2.set_ylabel("nodes (log scale)")
ax2.set_title("Mean nodes generated (log scale)")

plt.tight_layout()
fig.savefig(OUT, dpi=180, bbox_inches="tight")
print(f"✅ {OUT}")
