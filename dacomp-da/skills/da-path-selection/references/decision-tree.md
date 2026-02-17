# Decision Tree (No Rubric)

1. Is the question asking for definitions or formulae?
- Yes → use `da-metric-kpi` first.

2. Is the question asking for comparisons across groups/time?
- Yes → use `da-aggregation` + `da-segmentation-ranking`.

3. Is it asking for trend or seasonality?
- Yes → add `da-trend-relationship` (trend part).

4. Is it asking for “impact/effect/driver” after controls?
- Yes → add `da-effect-modeling`.

5. Is it asking for instability or anomalies?
- Yes → add `da-volatility-anomaly`.

6. Is it asking for scores or rankings?
- Yes → add `da-scoring-composite`.

7. Is it retention/churn/funnel?
- Yes → add `da-retention-funnel`.

8. Always finish with `da-insight-recommendation`.
