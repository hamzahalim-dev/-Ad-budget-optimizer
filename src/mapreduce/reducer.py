#!/usr/bin/env python3
"""
reducer.py: sums the five metrics for each key.

Hadoop sorts mapper output by key, so all records for one key arrive together.
Output format = input format, so this same script also works as a COMBINER.
"""
import sys


def emit(key, t):
    sys.stdout.write(f"{key}\t{t[0]}\t{t[1]}\t{t[2]:.2f}\t{t[3]}\t{t[4]:.2f}\n")


def main():
    current, t = None, None
    for line in sys.stdin:
        key, imp, clk, spd, conv, rev = line.rstrip("\r\n").split("\t")
        if key != current:
            if current is not None:
                emit(current, t)
            current, t = key, [0, 0, 0.0, 0, 0.0]
        t[0] += int(imp); t[1] += int(clk); t[2] += float(spd); t[3] += int(conv); t[4] += float(rev)
    if current is not None:
        emit(current, t)


if __name__ == "__main__":
    main()
