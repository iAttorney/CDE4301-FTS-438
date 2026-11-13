"""Iteration convergence check for Star-CCM+ cornering simulations.

For every monitor CSV in a folder, finds the earliest iteration after which the
rolling WINDOW-iteration mean of full-car downforce and full-car drag stays within
TOL % of the value reported from that run (the mean of its last WINDOW iterations).
It also reports how far the averaged values at a proposed reduced limit (default
2000 iterations) are from the final values.

Usage:
    python iteration_check.py path/to/csv_folder
    python iteration_check.py path/to/csv_folder --tol 0.5 --limit 2000 \
        --fig ../../assets/report-figure-iteration-convergence.png

Outputs:
    iteration_check_results.csv   one row per run
    the figure (default: report-figure-iteration-convergence.png)

Requires: pandas, numpy, matplotlib.
"""
import argparse, glob, os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Star-CCM+ monitor names for the full-car totals, e.g. "50 DF TTL Monitor",
# "35 DF FULL TTL Monitor", "100 Drag TTL Monitor", "70 DRAG FULL TTL Monitor".
MONITORS = {
    "Full-car downforce": r"^\d+\s+DF\s+(FULL\s+)?TTL\s+Monitor$",
    "Full-car drag": r"^\d+\s+DRAG\s+(FULL\s+)?TTL\s+Monitor$",
}


def find_column(df, pattern):
    """Return the first column whose monitor name (text before ':') matches pattern."""
    for col in df.columns[1:]:
        if re.match(pattern, col.split(":")[0].strip(), re.I):
            return col
    return None


def settling_iteration(iters, values, window, tol_pct):
    """Earliest iteration after which the rolling mean stays within tol_pct of the final mean."""
    ref = np.nanmean(values[-window:])
    roll = pd.Series(values).rolling(window).mean().values
    err = np.abs(roll - ref) / abs(ref) * 100.0
    outside = np.where(~(err <= tol_pct))[0]  # the first window-1 points are NaN -> outside
    idx = window - 1 if len(outside) == 0 else min(outside[-1] + 1, len(iters) - 1)
    return int(iters[idx]), ref, roll


def analyse(folder, window, tol, limit):
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        df = pd.read_csv(path).dropna(axis=1, how="all")
        if not pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
            print(f"- {os.path.basename(path)}: first column is not an iteration count, skipped")
            continue
        iters = df.iloc[:, 0].values
        row = {"run": os.path.splitext(os.path.basename(path))[0], "last_iteration": int(iters[-1])}
        for label, pattern in MONITORS.items():
            col = find_column(df, pattern)
            if col is None:
                print(f"! {row['run']}: no '{label}' monitor found, skipped")
                break
            stop, ref, roll = settling_iteration(iters, df[col].values, window, tol)
            row[f"{label} final (N)"] = ref
            row[f"{label} settled at"] = stop
            if iters[-1] > limit:
                i = int(np.argmin(np.abs(iters - limit)))
                row[f"{label} diff at {limit} (N)"] = roll[i] - ref
        else:
            rows.append(row)
    return pd.DataFrame(rows)


def plot(table, tol, window, limit, original, fig_path):
    q1, q2 = MONITORS
    t = table.assign(later=table[[f"{q1} settled at", f"{q2} settled at"]].max(axis=1)).sort_values("later")
    n = len(t)
    y = np.arange(n)[::-1]
    plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 0.42 * n + 1.9), dpi=170)
    a, b = t[f"{q1} settled at"].values, t[f"{q2} settled at"].values
    for yi, ai, bi in zip(y, a, b):
        ax.plot([min(ai, bi), max(ai, bi)], [yi, yi], color="#c8d3df", lw=2, zorder=1)
    ax.scatter(a, y, s=46, marker="o", color="#19558a", edgecolor="white", lw=1.2, zorder=3, label=q1)
    ax.scatter(b, y, s=50, marker="D", color="#d9730d", edgecolor="white", lw=1.2, zorder=3, label=q2)
    ax.axvline(limit, color="#172333", lw=1.2, ls="--")
    ax.axvline(original, color="#172333", lw=1.2)
    yb = -1.2
    ax.text(limit - 20, yb, f"{limit} (reduced limit)", ha="right", va="center", fontsize=9, color="#172333")
    ax.text(original - 20, yb, f"{original} (original limit)", ha="right", va="center", fontsize=9, color="#172333")
    ax.set_yticks(y)
    ax.set_yticklabels([f"Cornering {i + 1}" for i in range(n)], fontsize=9)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-1.7, n - 0.3)
    ax.set_xlim(0, original + 100)
    ax.set_xlabel(f"Iteration after which the rolling {window}-iteration mean stays within ±{tol:g}% of the final value",
                  color="#405167")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(0.94, 1.0))
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    return t


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", help="folder containing Star-CCM+ monitor CSV exports")
    p.add_argument("--window", type=int, default=300, help="averaging window (default 300)")
    p.add_argument("--tol", type=float, default=1.0, help="tolerance in percent (default 1.0)")
    p.add_argument("--limit", type=int, default=2000, help="proposed reduced iteration limit (default 2000)")
    p.add_argument("--original", type=int, default=3500, help="original iteration limit (default 3500)")
    p.add_argument("--fig", default="report-figure-iteration-convergence.png", help="output figure path")
    args = p.parse_args()

    table = analyse(args.folder, args.window, args.tol, args.limit)
    if table.empty:
        raise SystemExit("No usable CSVs found.")
    ordered = plot(table, args.tol, args.window, args.limit, args.original, args.fig)
    ordered = ordered.drop(columns="later")
    ordered.insert(0, "label", [f"Cornering {i + 1}" for i in range(len(ordered))])
    ordered.to_csv("iteration_check_results.csv", index=False, float_format="%.3f")

    pd.set_option("display.width", 220)
    print(ordered.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    settled = ordered[[f"{q} settled at" for q in MONITORS]].max(axis=1)
    print(f"\nRuns: {len(ordered)}   latest settling iteration (±{args.tol:g}%): {settled.max()}")
    for q in MONITORS:
        col = f"{q} diff at {args.limit} (N)"
        if col in ordered and ordered[col].notna().any():
            print(f"{q}: largest difference at iteration {args.limit} = {ordered[col].abs().max():.3f} N "
                  f"({ordered[col].notna().sum()} runs longer than {args.limit} iterations)")
    print(f"Figure saved to {args.fig}; table saved to iteration_check_results.csv")


if __name__ == "__main__":
    main()
