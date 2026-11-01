
**Recommendation for Rs. 1,000,000:** Facebook Rs 295K (30%), Instagram Rs 300K (30%), Google Rs 295K (30%), TikTok Rs 60K (6%), YouTube Rs 50K (5%).

1. **Expected result:** Rs 3.42M revenue (ROAS 3.42), **Rs 88,863 more (+2.7%)**
   than the current split, for the same budget.
2. **Moves:** increase Google (+Rs 95K), Instagram (+Rs 50K); reduce TikTok (−Rs 90K), YouTube (−Rs 50K), Facebook (−Rs 5K).
3. **Why not all on Google?** It has the best *average* ROAS, but also the steepest diminishing returns
   (β = 0.65). Putting the whole budget there would earn Rs 2.59M
   (-22% vs current). Filling top-ROAS platforms first earns +0.5%.
   The optimised plan wins because it equalises *marginal* ROAS (≈ 2.57 on the unconstrained platforms).
4. **The model is reliable:** on two unseen months it predicted daily revenue with
   3.7% average error (vs 6.2% for constant ROAS),
   recovered the true β within 1%, and the bootstrap ranges are narrow
   (every platform within ±2 points).
5. **Big data made the answer correct:** trained on 10K records the engine captured 15% of the best possible gain;
   on 10M records, 100%.
6. **Within platforms:** shift spend towards retargeting and promo campaigns and the 25–44 age groups;
   judge brand campaigns on reach, not ROAS.
7. **Re-run monthly:** response curves change with seasons, competition and creative. The engine is in `src/engine.py`.
