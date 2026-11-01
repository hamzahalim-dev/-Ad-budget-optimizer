
**Engine:** Hadoop 3.3.6 (standalone), 2 parallel map slot(s)

1. **Correctness:** 7 of 7 breakdowns (1,890 groups in total) match Pandas.
   Counts are identical; money totals differ by at most Rs. 0.00 (floating-point rounding).
2. **One pass, many answers:** a single job produced all seven breakdowns in 104s,
   instead of reading 10M rows seven times.
3. **Combining matters:** in-mapper combining cut the records sent to the reducer from
   1,000,000 to 15, and job time from 18.4s to 11.5s.
   On a real cluster, the shuffle crosses the network, so this saving is even larger.
4. **Scaling:** 10,000 rows took 5.5s and 10,000,000 rows took 43.5s
   (1,000x the data, 8x the time),
   peaking at 230,097 rows/second. Small jobs are dominated by Hadoop's fixed start-up cost, so MapReduce only pays off on large data.
