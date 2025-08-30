#!/usr/bin/env python3
from __future__ import annotations
import shutil, sys
from pathlib import Path

# Which figures to collect (source -> caption)
FIGS = [
    ("crossover_crossover.png",
     "Crossover: IDA*/A* time ratio across tested depths (ratio < 1 ⇒ IDA* faster)."),
    ("bpmx_ratio.png",
     "BPMX speedup on IDA*: time ratio (BPMX / Plain); lower is better."),
    ("smoke_p15_combined.png",
     "15-puzzle: per-depth curves (expanded / generated / time) for A* vs IDA*."),
    ("p8_all_small_combined.png",
     "8-puzzle: per-depth curves comparing A*, IDA*, BFS, DFS (expanded / generated / time)."),
    ("unsolvable_time.png",
     "Unsolvable instances: mean time by algorithm."),
    ("unsolvable_generated.png",
     "Unsolvable instances: mean generated nodes by algorithm."),
]

def main():
    src_dir = Path("results/plots")
    out_dir = Path("report/figs")
    out_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    missing = []
    for fname, _ in FIGS:
        src = src_dir / fname
        if src.exists():
            dst = out_dir / fname
            shutil.copy2(src, dst)
            copied.append(dst)
        else:
            missing.append(src)

    # Write a markdown block you can paste into the report
    block_path = out_dir / "fig_block.md"
    with block_path.open("w", encoding="utf-8") as f:
        f.write("## Figures (key story)\n\n")
        for fname, caption in FIGS:
            f.write(f"![{caption}](figs/{fname})\n\n")

    print(f"Created: {block_path}")
    if copied:
        print("Copied figures:")
        for p in copied:
            print(" -", p)
    if missing:
        print("\nMissing figures (not copied):")
        for p in missing:
            print(" -", p)
        print("\nTip: rerun the corresponding analysis to generate them, or edit FIGS in this script.")

if __name__ == "__main__":
    sys.exit(main())
