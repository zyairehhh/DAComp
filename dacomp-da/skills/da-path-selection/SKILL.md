---
name: da-path-selection
description: Select and execute rubric Paths as explicit analysis step sequences. Use when DAComp-DA rubric defines Path options and the response must align with a chosen Path per requirement.
---

# DA Path Selection

## Overview
Convert rubric Paths into explicit analysis step sequences. Ensure each Requirement is completed by one Path, end-to-end.

## Workflow

### 1. Parse the Rubric
- List each Requirement and all available Paths under it.
- Note any pseudo-code, anchors, or mandatory steps.

### 2. Select One Path per Requirement
- Choose the Path that best matches the question and available data.
- Do not mix steps from different Paths unless explicitly allowed.

### 3. Execute the Path End-to-End
- Follow the Path steps in order.
- Produce the evidence artifacts required by that Path (tables/figures/KPIs).

### 4. Label the Path in Output
- Explicitly state: “Requirement X uses Path Y.”
- Map each conclusion back to its Path evidence.

## Output Notes
- If no Path matches, declare the mismatch and execute a reasonable alternative, but note the risk.

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
