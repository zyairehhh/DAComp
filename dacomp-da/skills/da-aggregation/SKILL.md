---
name: da-aggregation
description: Build grouped aggregation tables for DA tasks. Use when requirements ask for grouped comparisons by time, category, region, cohort, or segment.
---

# DA Aggregation

## Workflow

### 1. Choose Grain
- Identify group-by dimensions required by the rubric.

### 2. Build Base Aggregates
- Counts, sums, averages, medians as needed.

### 3. Derive KPIs
- Compute rates/ratios on top of aggregates.
- For threshold-based requirements, output both count and percentage.

### 4. Output Table
- Clearly state grain and column definitions.
- Include sample size `n` and unit labels.
- Include top/bottom or min/max when comparison is requested.

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
- Keep grouping keys, filters, and time windows exactly as stated in the task contract.
- Do not merge/split groups unless the question explicitly requests it.

## Delivery Checklist (Generic, High-Score Friendly)
- Restate the question as measurable targets: metrics, population, time window, and comparison dimension.
- Define each metric explicitly with units and threshold direction (higher/lower is better if applicable).
- Report the filtered sample size (`n`) after applying criteria.
- Provide at least one KPI table per requirement; cite key numbers in the narrative.
- If ranking/segmentation is used, include top/bottom examples and min/max values.
- If thresholds are used, report counts **and** percentages for each class.
- If a formula/composite score is used, show the exact formula and one worked example.
- Tie each conclusion to a numeric anchor; avoid introducing new metrics unless the task requires it.
