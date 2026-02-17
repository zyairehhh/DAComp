---
name: da-orchestrator
description: Orchestrate which DA skills to apply for open-ended analysis when rubrics are unavailable. Use to decompose a question into requirements, infer analysis paths, and compose skill sequences that maximize completeness, accuracy, and evidence-backed conclusions.
---

# DA Orchestrator

## Overview
Guide an agent to select and sequence DA skills based solely on the user question and available data, maximizing rubric-aligned scoring without needing the rubric at runtime.

## Workflow

### 1. Decompose the Question
- Split the question into 1-3 Requirements (what must be answered).
- For each requirement, identify target metric(s), population, time window, and comparison dimension.

### 2. Classify Each Requirement
- Map each requirement to one or more **archetypes** (see `references/archetype-catalog.md`).
- Choose the minimal sequence of skills that can satisfy the requirement end-to-end.

### 3. Compose a Skill Sequence
- Use composition recipes in `references/composition-recipes.md`.
- Keep the sequence short but complete (definition → computation → analysis → conclusion).

### 4. Enforce Evidence and Reproducibility
- Require at least one table/KPI per requirement.
- If a claim is made, tie it to a number or table.
- Prefer SQL/pseudo-code to make steps reproducible.

### 5. Produce a Structured Output Plan
- Output the chosen skills and their execution order.
- Identify expected artifacts (tables/figures) before running analysis.

## Rubric-Aligned Heuristics (Rubric-Absent)
- Always define metrics explicitly before analysis.
- Prefer methods that yield numeric anchors (tables/metrics) over purely narrative explanations.
- Provide conclusions for each requirement and tie them to evidence.
- If multiple methods are plausible, choose one and state assumptions.

## References
- Use `references/archetype-catalog.md` to map questions to analysis types.
- Use `references/decision-tree.md` to route to skills.
- Use `references/composition-recipes.md` to sequence skills.
- Use `references/output-contract.md` to standardize final report structure.
