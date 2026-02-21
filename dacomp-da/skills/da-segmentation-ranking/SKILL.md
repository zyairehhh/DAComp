---
name: da-segmentation-ranking
description: Segment entities and rank top/bottom groups. Use when tasks require quantiles, cohorts, thresholds, or top-k analysis.
---

# DA Segmentation & Ranking

## Workflow

### 1. Pick Segmentation Rule
- Quantiles, thresholds, or top-k.
- Justify rule with distribution if arbitrary.

### 2. Rank and Profile
- Rank entities by metric.
- Summarize segment profiles with key KPIs.
- Report segment size and segment share (`count` and `%`) for every segment.
- If the task requests all segments/categories, do not subset to a sample.

### 3. Interpret
- Highlight what differentiates top vs bottom segments.
- Include at least one concrete top example and one bottom example with numeric anchors.

## Deterministic Mode Rules
- Keep ranking metric and tie-break logic explicit.
- If `top-k` is requested, return exactly `k` unless ties are explicitly handled.

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
