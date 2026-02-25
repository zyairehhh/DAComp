# exp-da-001 Requirement Coverage Matrix

## When to use
- The question has multiple required deliverables (analysis + diagnosis + recommendation).
- Rubric-like evaluation may penalize missing sub-questions.
- You are unsure whether the report fully answers each requirement.

## Experience
Before deep analysis, build a requirement-to-evidence matrix:
1. Split the prompt into explicit requirement bullets.
2. For each bullet, define: metric/formula, group split, expected output table/statement.
3. Reserve one report section per requirement and map evidence into that section.
4. Before `Terminate`, run a final coverage check: every requirement has at least one quantitative evidence line and one conclusion line.

## Minimal template
```text
R1: [what to answer]
- Metric/Formula:
- SQL/Python artifact:
- Evidence line in report:
- Decision/Conclusion:
```

## Common failure prevented
- High-level narrative but missing required sub-answers.
- Correct analysis that does not explicitly answer the asked deliverable.
