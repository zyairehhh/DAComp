# Archetype Catalog (Rubric-Absent)

Each archetype maps common question intent to a standard analysis path and skill set.

## 1) Metric Definition & KPI
**Trigger:** define/compute/rate/ratio/score
**Goal:** produce a correct KPI with explicit formula and validation.
**Skills:** da-metric-kpi → da-aggregation (if grouped) → da-insight-recommendation

## 2) Group Comparison
**Trigger:** compare/difference/across/by/between
**Goal:** compare KPIs across segments/time/categories.
**Skills:** da-aggregation → da-segmentation-ranking → da-insight-recommendation

## 3) Trend / Seasonality
**Trigger:** trend/over time/monthly/weekly/seasonal
**Goal:** describe changes over time with evidence.
**Skills:** da-aggregation → da-trend-relationship → da-insight-recommendation

## 4) Ranking / Best / Worst
**Trigger:** top/best/worst/identify/priority
**Goal:** rank entities and profile top/bottom segments.
**Skills:** da-scoring-composite (if multi-KPI) or da-segmentation-ranking → da-insight-recommendation

## 5) Relationship / Correlation
**Trigger:** relationship/correlation/associated
**Goal:** quantify relationship and interpret direction/strength.
**Skills:** da-trend-relationship → da-insight-recommendation

## 6) Effect / Impact (with controls)
**Trigger:** impact/effect/marginal/controlling/interaction
**Goal:** estimate marginal effect and interpret.
**Skills:** da-effect-modeling → da-insight-recommendation

## 7) Scoring / Composite Index
**Trigger:** score/index/weighted/composite
**Goal:** construct composite score and ranking.
**Skills:** da-scoring-composite → da-segmentation-ranking → da-insight-recommendation

## 8) Volatility / Instability / Anomaly
**Trigger:** volatility/instability/fluctuation/outlier/anomaly
**Goal:** quantify variability, detect anomalies, explain impact.
**Skills:** da-volatility-anomaly → da-trend-relationship → da-insight-recommendation

## 9) Retention / Churn / Funnel
**Trigger:** retention/churn/conversion/funnel
**Goal:** compute rates and compare cohorts.
**Skills:** da-retention-funnel → da-segmentation-ranking → da-insight-recommendation

## 10) Strategy / Recommendation
**Trigger:** recommend/strategy/action/policy
**Goal:** convert evidence into actions with KPIs.
**Skills:** da-insight-recommendation (after analysis skills)
