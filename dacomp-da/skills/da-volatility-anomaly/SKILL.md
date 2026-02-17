---
name: da-volatility-anomaly
description: Analyze variability and detect anomalies. Use when tasks mention instability, volatility, or outliers.
---

# DA Volatility & Anomaly

## Workflow

### 1. Measure Volatility
- Use std/CV at required grain.

### 2. Detect Anomalies
- Use IQR or mean ± 2σ thresholds.

### 3. Impact Assessment
- Explain whether anomalies change key conclusions.

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
