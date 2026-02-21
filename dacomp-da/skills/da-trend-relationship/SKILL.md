---
name: da-trend-relationship
description: Analyze time trends and relationships (correlation/significance). Use when tasks ask for trend/seasonality or correlation tests.
---

# DA Trend & Relationship

## Workflow

### 1. Trend Analysis
- Aggregate by time grain.
- Identify direction, inflection, and seasonality.
- If the task names an exact period (for example 2005-2018), output all time points in that period.
- If phase descriptions are requested, summarize trend by phase explicitly (for example early stable vs late rapid growth).

### 2. Relationship/Test
- Compute correlation or required test.
- Report effect size + p-value.
- Interpret practical meaning.
- If the task requests a specific coefficient type (Pearson/Spearman/Kendall), compute that type first.
- If exact anchor values are expected, report to matching precision.

## Deterministic Mode Rules
- Do not replace required correlation output with qualitative statements only.
- Keep the same sample window for trend and relationship analysis unless the task says otherwise.

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
