# tools/make_bhat.py
import os, glob, math, sys
import numpy as np
import pandas as pd

# Try SciPy for t critical; fall back to normal if missing.
try:
    from scipy import stats
    def tcrit95(df): return stats.t.ppf(0.975, df)
except Exception:
    def tcrit95(df): return 1.96  # good enough when df is not tiny

# ---------- Helpers ----------
def label_board(row):
    """
    Try to produce a 'board' label from available columns or filename.
    Prefers explicit 'domain' if present (e.g., 'p8', 'p15'), else rows/cols.
    """
    if 'domain' in row and isinstance(row['domain'], str) and row['domain']:
        return row['domain']
    r, c = row.get('rows', None), row.get('cols', None)
    if pd.notna(r) and pd.notna(c):
        return f"R{int(r)}x{int(c)}"
    return "unknown"

def load_data():
    # Prefer merged CSVs; else fall back to raw per-run CSVs.
    paths = sorted(glob.glob("results/merged/*.csv"))
    if not paths:
        paths = sorted(glob.glob("results/*.csv"))
    if not paths:
        print("No CSVs found under results/ or results/merged/.")
        sys.exit(1)

    dfs = []
    for p in paths:
        try:
            df = pd.read_csv(p)
            df['__source'] = os.path.basename(p)
            dfs.append(df)
        except Exception as e:
            print(f"Skip {p}: {e}")
    if not dfs:
        print("No readable CSVs found.")
        sys.exit(1)
    df = pd.concat(dfs, ignore_index=True)

    # Normalize column names we need.
    # Expected: depth, expanded, algorithm, heuristic, termination, (domain or rows/cols)
    for col in ['depth', 'expanded', 'algorithm', 'heuristic']:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in CSVs.")
    if 'termination' not in df.columns:
        # If termination missing, assume all are ok
        df['termination'] = 'ok'

    # Attach board label
    if 'domain' not in df.columns and ('rows' not in df.columns or 'cols' not in df.columns):
        # Try to infer from filename (e.g., p15_*.csv)
        df['domain'] = df['__source'].str.extract(r'(p\d+|r\d+x\d+)', expand=False).str.lower()
    df['board'] = df.apply(label_board, axis=1)
    return df

def mean_expansions_per_depth(df):
    """ Build per-depth means for (board, heuristic, algo). """
    # Keep only successful runs
    ok = df[df['termination'].astype(str).str.lower().eq('ok')].copy()
    # Some files may have different casing
    ok['algorithm'] = ok['algorithm'].astype(str)

    grp = (ok.groupby(['board','heuristic','algorithm','depth'], as_index=False)
             .agg(expanded_mean=('expanded','mean'),
                  n_instances=('expanded','size')))
    return grp

def estimate_bhat_group(g):
    """
    Estimate b_hat for one (board, heuristic, algorithm) group using log-OLS:
        log(mean_expanded) ~ a + s * depth;  b_hat = exp(slope)
    Returns one row with kdepths, b_hat, b_lo, b_hi, r2, depth_min, depth_max.
    """
    g = g.sort_values('depth').copy()

    # Filter out non-positive means (shouldn't happen but guard anyway)
    g = g[g['expanded_mean'] > 0]
    k = len(g)
    if k < 3:
        return pd.Series({
            'kdepths': k, 'b_hat': np.nan, 'b_lo': np.nan, 'b_hi': np.nan,
            'r2': np.nan, 'depth_min': g['depth'].min() if k else np.nan,
            'depth_max': g['depth'].max() if k else np.nan
        })

    x = g['depth'].to_numpy(dtype=float)
    y = np.log(g['expanded_mean'].to_numpy())

    # OLS fit (manual to avoid SciPy dependency for stderr)
    x_mean, y_mean = x.mean(), y.mean()
    Sxx = ((x - x_mean)**2).sum()
    if Sxx == 0:
        return pd.Series({'kdepths': k, 'b_hat': np.nan, 'b_lo': np.nan, 'b_hi': np.nan,
                          'r2': np.nan, 'depth_min': g['depth'].min(), 'depth_max': g['depth'].max()})
    slope = ((x - x_mean)*(y - y_mean)).sum() / Sxx
    intercept = y_mean - slope * x_mean

    # R^2
    y_hat = intercept + slope * x
    ss_res = ((y - y_hat)**2).sum()
    ss_tot = ((y - y_mean)**2).sum()
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else np.nan

    # stderr of slope
    dfree = k - 2
    s_err = math.sqrt(ss_res / dfree)
    se_slope = s_err / math.sqrt(Sxx)
    t = tcrit95(dfree)

    b_hat = math.exp(slope)
    b_lo  = math.exp(slope - t*se_slope)
    b_hi  = math.exp(slope + t*se_slope)

    return pd.Series({
        'kdepths': k, 'b_hat': b_hat, 'b_lo': b_lo, 'b_hi': b_hi,
        'r2': r2, 'depth_min': g['depth'].min(), 'depth_max': g['depth'].max()
    })

def main():
    df = load_data()
    grp = mean_expansions_per_depth(df)

    # Choose which algorithm to characterize. IDA* is common for growth.
    # If your 'algorithm' values differ (e.g., 'IDA* (BPMX ON)'), normalize them here.
    algomap = {
        'IDA* (BPMX ON)': 'IDA* (BPMX ON)',
        'IDA* (BPMX)': 'IDA* (BPMX ON)'
    }
    grp['algorithm'] = grp['algorithm'].replace(algomap)

    # Compute b_hat for each (board, heuristic, algorithm)
    out = (grp.groupby(['board','heuristic','algorithm'])
              .apply(estimate_bhat_group)
              .reset_index())

    # Pretty print a focused view: IDA* and A*
    show = out[out['algorithm'].isin(['IDA*', 'A*'])].copy()
    if show.empty:
        # If algorithms are named differently, show all
        show = out.copy()

    cols = ['board','heuristic','algorithm','kdepths','depth_min','depth_max','b_hat','b_lo','b_hi','r2']
    show = show[cols].sort_values(['board','heuristic','algorithm'])

    # Ensure output dir
    os.makedirs("report/tables", exist_ok=True)
    csv_path = "report/tables/table_A7_bhat.csv"
    xlsx_path = "report/tables/table_A7_bhat.xlsx"
    show.to_csv(csv_path, index=False)
    try:
        show.to_excel(xlsx_path, index=False)
    except Exception:
        pass

    # Console print
    pd.set_option('display.float_format', lambda v: f"{v:0.3f}")
    print("\nEmpirical branching factor (b_hat) — geometric growth model")
    print(show.to_string(index=False))
    print(f"\nSaved: {csv_path}")
    if os.path.exists(xlsx_path):
        print(f"Saved: {xlsx_path}")

if __name__ == "__main__":
    main()
