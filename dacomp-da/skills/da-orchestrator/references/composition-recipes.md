# Composition Recipes

## Recipe A: Definition → Comparison → Recommendation
Use when the question asks for defined metrics and comparisons.
Sequence: da-metric-kpi → da-aggregation → da-segmentation-ranking → da-insight-recommendation
Artifacts: KPI table, segment comparison table

## Recipe B: Trend → Driver Diagnosis → Recommendation
Use when instability or changes over time are central.
Sequence: da-aggregation → da-trend-relationship → da-volatility-anomaly → da-insight-recommendation
Artifacts: trend table/plot, anomaly list, driver notes

## Recipe C: Relationship → Effect
Use when a relationship is asked and causal framing is implied.
Sequence: da-trend-relationship → da-effect-modeling → da-insight-recommendation
Artifacts: correlation table + regression summary

## Recipe D: Composite Ranking
Use when selecting best segments or entities.
Sequence: da-scoring-composite → da-segmentation-ranking → da-insight-recommendation
Artifacts: score table + top/bottom profiles

## Recipe E: Retention/Funnel
Use for retention, churn, or conversion tasks.
Sequence: da-retention-funnel → da-segmentation-ranking → da-insight-recommendation
Artifacts: cohort table + segment comparison

## Recipe F: Multi-Requirement (Mixed)
When multiple requirements exist, run recipes per requirement, then integrate.
Artifacts: one evidence table per requirement + unified summary
