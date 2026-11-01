#!/usr/bin/env python3
"""
mapper.py: Hadoop Streaming mapper with IN-MAPPER COMBINING.

Instead of emitting one record per input row, the mapper keeps running totals
in a dictionary and emits each key once, at the end of its input split.
That shrinks the shuffle from millions of records to a few hundred.

Usage : python3 mapper.py <dimensions>     e.g.  platform  |  platform,age  |  all
Input : CSV  date,campaign,platform,impressions,clicks,spend,conversions,revenue,age,gender,city,device
Output: <dimension>=<value> TAB impressions TAB clicks TAB spend TAB conversions TAB revenue
"""
import sys

FIELDS = "date,campaign,platform,impressions,clicks,spend,conversions,revenue,age,gender,city,device".split(",")
IDX = {name: i for i, name in enumerate(FIELDS)}
ALL_DIMS = ["platform", "campaign", "age", "gender", "city", "device", "date|platform"]


def make_key_fn(dim):
    cols = [IDX[c] for c in dim.split("|")]
    if len(cols) == 1:
        i = cols[0]
        return lambda f: dim + "=" + f[i]
    return lambda f: dim + "=" + "|".join(f[i] for i in cols)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "platform"
    dims = ALL_DIMS if arg == "all" else arg.split(",")
    key_fns = [make_key_fn(d) for d in dims]
    totals, bad = {}, 0

    for line in sys.stdin:
        f = line.rstrip("\r\n").split(",")
        if f[0] == "date":                       # header row
            continue
        if len(f) != len(FIELDS):                # malformed row
            bad += 1
            continue
        try:
            m = (int(f[3]), int(f[4]), float(f[5]), int(f[6]), float(f[7]))
        except ValueError:
            bad += 1
            continue
        for key_fn in key_fns:
            key = key_fn(f)
            t = totals.get(key)
            if t is None:
                totals[key] = list(m)
            else:
                t[0] += m[0]; t[1] += m[1]; t[2] += m[2]; t[3] += m[3]; t[4] += m[4]

    out = sys.stdout.write
    for key, t in totals.items():
        out(f"{key}\t{t[0]}\t{t[1]}\t{t[2]:.2f}\t{t[3]}\t{t[4]:.2f}\n")
    if bad:                                      # shows up as a Hadoop job counter
        sys.stderr.write(f"reporter:counter:AdData,MalformedRows,{bad}\n")


if __name__ == "__main__":
    main()
