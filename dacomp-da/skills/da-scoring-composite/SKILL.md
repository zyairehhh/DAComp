---
name: da-scoring-composite
description: Construct composite scores and weighted rankings. Use when tasks require weighted scores, standardization, or composite indices.
---

# DA Scoring & Composite Index

## Workflow

### 1. Lock the Scoring Contract
- Copy the task-specified score formula, weights, thresholds, and boundary rules exactly.
- Define all variables with units and direction (higher/lower is better).
- If the task gives no formula, declare the chosen formula explicitly and keep it stable.

### 2. Compute Deterministically
- Compute score components with reproducible steps (SQL or explicit formulas).
- Report sample size `n`.
- Validate boundary behavior (`>=`, `>`, `<`, `<=`) on at least one edge example.

### 3. Rank and Segment
- Output top/bottom entities and min/max scores.
- If tiers are required, report counts and percentages per tier.

### 4. Scenario and Sensitivity (When Requested)
- For improvement/simulation tasks, report baseline vs scenario deltas.
- If multiple levers exist, show single-lever and combined-lever impacts separately.

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
- Do not re-define the task's scoring weights or threshold constants.
- Do not change strict inequalities into non-strict inequalities.
- Do not skip required outputs: formula, tier counts, top/bottom, min/max.

## Delivery Checklist (Generic, High-Score Friendly)
- Restate the question as measurable targets: metrics, population, time window, and comparison dimension.
- Define each metric explicitly with units and threshold direction (higher/lower is better if applicable).
- Report the filtered sample size (`n`) after applying criteria.
- Provide at least one KPI table per requirement; cite key numbers in the narrative.
- If ranking/segmentation is used, include top/bottom examples and min/max values.
- If thresholds are used, report counts **and** percentages for each class.
- If a formula/composite score is used, show the exact formula and one worked example.
- Tie each conclusion to a numeric anchor; avoid introducing new metrics unless the task requires it.
