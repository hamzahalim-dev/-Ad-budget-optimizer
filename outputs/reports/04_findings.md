
**Engine:** Spark 4.0.4 local[2]

1. **Correctness:** 7 of 7 breakdowns (1,890 groups) match Pandas,
   including the KPI ratios computed natively in Spark. DataFrame API and SQL give identical answers.
2. **Automatic optimisation:** Spark's planner applied partial aggregation (the equivalent of Notebook 03's
   hand-written in-mapper combining) and column pruning without any extra code.
3. **Reuse strategy:** for seven breakdowns, *GROUPING SETS (1 pass)* was fastest (24.3s vs
   83.0s for the slowest approach). Caching did not help here: the cache stores all 12 columns in memory, while each Parquet query reads only the few columns it needs. Caching pays off when data is reused many times or storage is slow.
4. **File format:** Parquet was 4.8x smaller than CSV and
   9.0x faster to query.
5. **Scaling:** on Parquet, 10K rows took 0.17s and 10M rows 3.06s:
   1,000x the data for 18x the time. Small queries are dominated by
   Spark's fixed per-query overhead.
