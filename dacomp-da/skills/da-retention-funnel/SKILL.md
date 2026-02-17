---
name: da-retention-funnel
description: Compute retention, churn, conversion, and funnel metrics. Use when tasks mention cohort, retention, conversion rates, or churn.
---

# DA Retention & Funnel

## Workflow

### 1. Define Cohort
- Entry event and time window.

### 2. Compute Rates
- Retention, churn, or conversion at each step.

### 3. Compare Segments
- Cohort vs segment differences.

## Rubric Scoring Checklist
- Completeness: cover every required step/item in the selected Path.
- Accuracy: match anchors or pseudo-code; show computed values.
- Conclusion: provide explicit conclusions tied to evidence.
- Evidence: if evidence is missing, treat as 0 points.


## References
- Use `references/templates.md` for SQL, tables, and visualization templates.
- Use `references/path-selection.md` for path selection rules.

## Scoring Boost Heuristics (Rubric-Absent)
- Always define metrics and show at least one validation check.
- Provide at least one table of computed values per requirement.
- When offering conclusions, tie each to a specific number.
- If multiple methods are possible, explicitly choose one and document assumption.
- Prefer outputs that are reproducible (SQL or pseudo-code).


## References
- Use `references/templates.md` for outputs.
- Use `references/decision-tree.md` to pick a path without rubrics.
- Use `references/examples.md` for sample patterns.

## Orchestration
- If you are unsure which skill to apply first, consult `da-orchestrator`.
