---
name: da-volatility-anomaly
description: Analyze variability and detect anomalies. Use when tasks mention instability, volatility, or outliers.
---

# DA Volatility & Anomaly

## Workflow

### 1. Measure Volatility
- Use std/CV at required grain.
- Keep time grain and segment definitions consistent with the task contract.

### 2. Detect Anomalies
- Use IQR or mean ± 2σ thresholds.
- If the question defines an anomaly condition, use that condition as primary and treat statistical rules as secondary diagnostics.

### 3. Impact Assessment
- Explain whether anomalies change key conclusions.
- Quantify impact on core KPI(s): baseline, anomaly-adjusted, and delta.

## Deterministic Mode Rules
- Do not change anomaly thresholds after seeing results.
- Report anomaly count, anomaly share, and at least one representative anomaly example.

## Rubric Scoring Checklist
- Completeness: cover every required step/item in the selected Path.
- Accuracy: match anchors or pseudo-code; show computed values.
- Conclusion: provide explicit conclusions tied to evidence.
- Evidence: if evidence is missing, treat as 0 points.


## References
- Use `references/templates.md` for outputs.
- Use `references/decision-tree.md` to pick a path without rubrics.
- Use `references/examples.md` for sample patterns.

## Orchestration
- If you are unsure which skill to apply first, consult `da-orchestrator`.

## Delivery Checklist (Generic, High-Score Friendly)
- Restate the question as measurable targets: metrics, population, time window, and comparison dimension.
- Define each metric explicitly with units and threshold direction (higher/lower is better if applicable).
- Report the filtered sample size (`n`) after applying criteria.
- Provide at least one KPI table per requirement; cite key numbers in the narrative.
- If ranking/segmentation is used, include top/bottom examples and min/max values.
- If thresholds are used, report counts **and** percentages for each class.
- If a formula/composite score is used, show the exact formula and one worked example.
- Tie each conclusion to a numeric anchor; avoid introducing new metrics unless the task requires it.
