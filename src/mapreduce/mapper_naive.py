#!/usr/bin/env python3
"""
mapper_naive.py: textbook mapper that emits ONE record per input row (no local aggregation).
Used only to show why combiners and in-mapper combining matter.

Usage : python3 mapper_naive.py <dimension>     e.g. platform
"""
import sys

IDX = {"campaign": 1, "platform": 2, "age": 8, "gender": 9, "city": 10, "device": 11}


def main():
    dim = sys.argv[1] if len(sys.argv) > 1 else "platform"
    i = IDX[dim]
    out = sys.stdout.write
    for line in sys.stdin:
        f = line.rstrip("\r\n").split(",")
        if f[0] == "date" or len(f) != 12:
            continue
        out(f"{dim}={f[i]}\t{f[3]}\t{f[4]}\t{f[5]}\t{f[6]}\t{f[7]}\n")


if __name__ == "__main__":
    main()
