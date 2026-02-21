---
name: da-metric-kpi
description: Define metrics and compute KPIs with clear numerator/denominator, filters, time window, and grain. Use when tasks require metric definitions, rate/ratio calculations, or anchor matching.
---

# DA Metric & KPI

## Workflow

### 1. Define the Metric
- Metric name and intent.
- Numerator and denominator.
- Filters and inclusion/exclusion rules.
- Time window and grain.

### 2. Compute the KPI
- Use the exact formula; handle zero denominators explicitly.
- Provide at least one validation check (range, sanity, or anchor).
- If thresholds exist, compute both `count` and `percentage`.

### 3. Report Clearly
- Show final KPI values with units and rounding.
- Document assumptions.
- Include sample size `n` after filtering.
- Add top/bottom or min/max if the requirement involves ranking/comparison.

### 4. Verification Gate
- Verify formula terms, units, and thresholds match the task contract exactly.
- Verify that every KPI used in conclusions appears in Results tables.
- For `all/every` requirements, verify coverage explicitly (for example, expected distinct groups vs produced groups).

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

## Deterministic Mode Rules
- Do not silently substitute proxy metrics for required KPIs.
- Do not drop required denominators, filters, or time windows.
- If a metric cannot be computed, state it explicitly and provide the blocking reason.

## Delivery Checklist (Generic, High-Score Friendly)
- Restate the question as measurable targets: metrics, population, time window, and comparison dimension.
- Define each metric explicitly with units and threshold direction (higher/lower is better if applicable).
- Report the filtered sample size (`n`) after applying criteria.
- Provide at least one KPI table per requirement; cite key numbers in the narrative.
- If ranking/segmentation is used, include top/bottom examples and min/max values.
- If thresholds are used, report counts **and** percentages for each class.
- If a formula/composite score is used, show the exact formula and one worked example.
- Tie each conclusion to a numeric anchor; avoid introducing new metrics unless the task requires it.
