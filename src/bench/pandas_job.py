#!/usr/bin/env python3
"""
pandas_job.py: the benchmark task for Pandas, run in a fresh Python process
so that every run starts cold and its peak memory can be measured.

Usage : python3 pandas_job.py <path> <csv|parquet>
Output: one JSON line with seconds, peak memory and the platform sums
"""
import json
import resource
import sys
import time

import pandas as pd

METRICS = ["impressions", "clicks", "spend", "conversions", "revenue"]


def peak_mb():
    """Peak memory of THIS process. VmHWM resets when the process starts, unlike ru_maxrss,
    which on Linux can inherit the parent's peak."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main():
    path, fmt = sys.argv[1], sys.argv[2]
    baseline = peak_mb()                       # Python + Pandas loaded, no data yet
    t0 = time.perf_counter()
    cols = ["platform"] + METRICS
    if fmt == "csv":
        df = pd.read_csv(path, usecols=cols, engine="pyarrow")
    else:
        df = pd.read_parquet(path, columns=cols)
    sums = df.groupby("platform", observed=True)[METRICS].sum()
    seconds = time.perf_counter() - t0
    print(json.dumps({"seconds": seconds, "peak_mb": peak_mb(), "baseline_mb": baseline,
                      "sums": {str(p): [float(v) for v in row] for p, row in sums.iterrows()}}))


if __name__ == "__main__":
    main()
