# DAComp-DA Path Summary (100 rubrics)

This summary consolidates common analysis paths found in rubric Path sections and maps them to reusable DA skills.

## Common Paths and When to Use

1. Metric Definition + KPI Calculation
Use when a requirement asks to "define" a metric, compute rate/ratio/score, or match anchors.
Typical steps: define numerator/denominator, filters, time window, grain; compute metric; validate with checks.

2. Grouped Aggregation
Use when a requirement asks for comparisons by category/time/segment.
Typical steps: group-by dimensions, compute aggregates (sum/avg/median), output table at required grain.

3. Segmentation & Ranking
Use when a requirement asks for top/bottom, quantiles, or cohort splits.
Typical steps: choose segmentation rule, rank entities, summarize segment profiles.

4. Trend/Seasonality
Use when a requirement asks for monthly/weekly trends or changes over time.
Typical steps: time-based aggregation, trend plot/table, identify inflection or seasonal effects.

5. Relationship/Significance
Use when a requirement asks about correlation or significance (Pearson/Spearman/t/chi/ANOVA).
Typical steps: compute correlation/test, report effect size + p-value, interpret direction and magnitude.

6. Regression/Effect Estimation
Use when a requirement asks for marginal effects or controlling variables.
Typical steps: specify model, include controls/interaction, interpret coefficients with units.

7. Scoring/Composite Index
Use when a requirement asks for weighted score, composite ranking, or standardization.
Typical steps: normalize features, apply weights, compute score, rank and interpret.

8. Volatility/Anomaly
Use when a requirement asks for instability, variability, or anomalies.
Typical steps: compute std/CV, detect anomalies (IQR or ±2σ), assess impact.

9. Retention/Conversion/Funnel
Use when a requirement asks for retention/churn/activation/conversion.
Typical steps: define cohort/time window, compute rates per cohort, compare segments.

10. Insights & Recommendations
Use when a requirement asks for conclusions, strategy, or actions.
Typical steps: tie evidence to conclusions, propose actions, define KPIs to monitor.

## Mapping to Skills
- da-path-selection: choose path per requirement and enforce end-to-end execution.
- da-metric-kpi: metric definition + KPI computation.
- da-aggregation: group-by aggregation tables.
- da-segmentation-ranking: segmentation, ranking, and profiling.
- da-trend-relationship: trend + correlation/significance.
- da-effect-modeling: regression/LOESS effect estimation.
- da-scoring-composite: composite score construction.
- da-volatility-anomaly: volatility/anomaly detection.
- da-retention-funnel: retention/churn/conversion.
- da-insight-recommendation: evidence-based conclusions + actions.
