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

### 4. Output Table
- Clearly state grain and column definitions.

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
