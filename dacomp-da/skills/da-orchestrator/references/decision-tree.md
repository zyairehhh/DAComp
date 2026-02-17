# Decision Tree (Routing Without Rubrics)

1. Does the question ask to **define or compute a metric**?
- Yes → da-metric-kpi (then da-aggregation if grouped)

2. Does it ask to **compare across groups or time**?
- Yes → da-aggregation → da-segmentation-ranking

3. Does it ask about **trend/seasonality**?
- Yes → da-trend-relationship (trend path)

4. Does it ask about **relationship/correlation**?
- Yes → da-trend-relationship (relationship path)

5. Does it ask about **impact/effect with controls**?
- Yes → da-effect-modeling

6. Does it ask for **ranking or top/bottom**?
- Yes → da-scoring-composite (if multi-KPI) or da-segmentation-ranking

7. Does it ask about **instability/anomaly**?
- Yes → da-volatility-anomaly

8. Does it ask about **retention/churn/funnel**?
- Yes → da-retention-funnel

9. Always finish with **da-insight-recommendation**.
