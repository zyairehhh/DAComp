# exp-da-001 Requirement Coverage Matrix

## Experience
Before deep analysis, build a requirement-to-evidence matrix:
1. Split the prompt into explicit requirement bullets. Count them.
2. For each bullet, define: metric/formula, group split, expected output table/statement.
3. Reserve one report section per requirement and map evidence into that section.
4. Before `Terminate`, run a final coverage check: every requirement has at least one quantitative evidence line and one conclusion line.
5. Do not submit if any requirement lacks numeric output or actionable conclusion.

## Minimal template
```text
R1: [what to answer]
- Metric/Formula:
- SQL/Python artifact:
- Evidence line in report:
- Decision/Conclusion:

R2: [what to answer]
- ...
```

## Final coverage audit
Before writing the final report, verify:
- Every requirement has a dedicated section with results
- Each section contains at least one quantitative finding
- Each finding has an interpretation and action implication
- Map `Requirement -> Report Section -> Evidence` to ensure nothing is missing

## Common failure prevented
- High-level narrative but missing required sub-answers.
- Correct analysis that does not explicitly answer the asked deliverable.
- Completeness leakage from missing one or two deliverables.
