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

### 3. Report Clearly
- Show final KPI values with units and rounding.
- Document assumptions.

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
