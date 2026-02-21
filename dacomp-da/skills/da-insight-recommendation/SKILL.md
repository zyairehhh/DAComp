---
name: da-insight-recommendation
description: Turn findings into evidence-backed insights and actions. Use when tasks ask for conclusions, recommendations, or strategies.
---

# DA Insights & Recommendations

## Workflow

### 1. Summarize Evidence
- Tie each insight to KPI/table/figure evidence.
- Keep each insight scoped to one requirement.

### 2. Recommend Actions
- Provide actions with expected KPI impact.
- Every recommendation must cite at least one numeric anchor from Results.

### 3. Monitoring Plan
- Define KPIs and thresholds for follow-up.
- Add owner/frequency when requested.

### 4. Conclusion Gate
- Reject claims that do not have explicit numeric support.
- Prefer concise, testable recommendations over broad narrative.

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
