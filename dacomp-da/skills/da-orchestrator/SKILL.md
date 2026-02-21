---
name: da-orchestrator
description: Orchestrate which DA skills to apply for open-ended analysis when rubrics are unavailable. Use to decompose a question into requirements, infer analysis paths, and compose skill sequences that maximize completeness, accuracy, and evidence-backed conclusions.
---

# DA Orchestrator

## Overview
Guide an agent to select and sequence DA skills based solely on the user question and available data, maximizing rubric-aligned scoring without needing the rubric at runtime.

## Workflow

### 1. Build a Task Contract
- Split the question into 1-3 requirements.
- For each requirement, explicitly lock: metric, formula, unit, population/filter, time window, comparison dimension, output artifact.
- If the question specifies thresholds/weights/boundaries, copy them verbatim into the contract.
- Capture quantifiers explicitly: `all`, `each`, `every`, `by month/year`, `top-k`.

### 2. Route by Task Mode
- `Deterministic Mode`: use when the question asks for scoring, tiering, thresholds, simulation, decomposition, correlation, top-k, or strict formulas.
- `Exploratory Mode`: use when the question emphasizes open diagnosis, patterns, or strategy without strict numeric rules.
- Default to `Deterministic Mode` when uncertain.

### 3. Compose a Skill Sequence
- Map each requirement to one or more archetypes (see `references/archetype-catalog.md`).
- Use composition recipes in `references/composition-recipes.md`.
- Keep sequence minimal but complete: definition -> computation -> validation -> conclusion.

### 4. Read Skills on Demand
- Skills live under `/workspace/dacomp-da/skills/<skill-name>/SKILL.md`.
- Read only selected skills and the specific references needed for the chosen mode.

### 5. Enforce Evidence and Reproducibility
- Require one KPI table or equivalent numeric artifact per requirement.
- Tie every key claim to a number.
- Prefer SQL or reproducible pseudo-code for calculations.

### 6. Run a Pre-Submit Quality Gate
- `Completeness gate`: all requirements answered.
- `Accuracy gate`: formula, thresholds, units, and boundaries match the task contract.
- `Conclusion gate`: each recommendation cites numeric evidence.

## Requirement Coverage Matrix (Required)
- Before final output, build a compact matrix with one row per requirement:
  `requirement | required outputs | produced outputs | missing items | pass/fail`.
- If any row fails, fix missing items first and only then finalize the report.

## Rubric-Aligned Heuristics (Rubric-Absent)
- Always define metrics explicitly before analysis.
- Prefer methods that yield numeric anchors (tables/metrics) over purely narrative explanations.
- Provide conclusions for each requirement and tie them to evidence.
- If multiple methods are plausible, choose one and state assumptions.

## Hard Constraints
- Do not invent new metric weights, threshold values, or score formulas in `Deterministic Mode`.
- Do not drop required counts/percentages for threshold tasks.
- If assumptions are required, state them briefly and keep the original task contract unchanged.

## References
- Use `references/archetype-catalog.md` to map questions to analysis types.
- Use `references/decision-tree.md` to route to skills.
- Use `references/composition-recipes.md` to sequence skills.
- Use `references/output-contract.md` to standardize final report structure and align with the Delivery Checklist.

## Delivery Checklist (Generic, High-Score Friendly)
- Restate the question as measurable targets: metrics, population, time window, and comparison dimension.
- Define each metric explicitly with units and threshold direction (higher/lower is better if applicable).
- Report the filtered sample size (`n`) after applying criteria.
- Provide at least one KPI table per requirement; cite key numbers in the narrative.
- If ranking/segmentation is used, include top/bottom examples and min/max values.
- If thresholds are used, report counts **and** percentages for each class.
- If a formula/composite score is used, show the exact formula and one worked example.
- Tie each conclusion to a numeric anchor; avoid introducing new metrics unless the task requires it.
