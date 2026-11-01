
**Machine:** 2 CPU cores, 14 GB RAM (Google Colab) | **Runs:** 36 timed, all correct

1. **Fastest engine by size:** 10k: Pandas, 100k: Pandas, 1m: Pandas, 10m: Pandas.
2. **At 10,000,000 rows:** Pandas 3.8s, Spark 14.4s, MapReduce 24.9s.
   MapReduce was 1.7x slower than Spark. Hadoop writes intermediate data to disk and starts a new JVM for every job, while Spark plans the whole job and keeps data in memory.
3. **Fixed overhead dominates small data:** at 10K rows Pandas took 0.02s,
   Spark 0.76s and MapReduce 3.91s. Distributed engines spend that time
   planning and scheduling, not computing.
4. **Scaling 1M → 10M (10x data):** Pandas 9.5x time, Spark 7.4x,
   MapReduce 3.5x.
5. **Memory is Pandas' real limit:** ~239 MB per million rows for this task, so roughly
   **45 million rows** fit on this machine. Spark and MapReduce stream data in partitions,
   and on a cluster they add machines instead of needing more RAM on one.
6. **File format matters as much as the tool:** at 10,000,000 rows, Parquet took Pandas
   1.1s (CSV: 3.8s) and Spark
   2.4s (CSV: 14.4s).

**Recommendation**
| Situation | Best choice |
|---|---|
| Data fits comfortably in one machine's RAM (here: up to ~45M rows) | **Pandas**: simplest and fast |
| Data larger than RAM, growing, or a scheduled production pipeline | **Spark**: scales out, SQL, optimiser |
| New projects | **Not MapReduce**: Spark replaced it, but its map → shuffle → reduce model underlies all of these tools |

*Caveat:* this is a single 2-core machine. Spark and MapReduce are built for clusters, where they spread work over many machines;
here they pay coordination costs without that benefit. The results show single-machine behaviour, not cluster performance.
