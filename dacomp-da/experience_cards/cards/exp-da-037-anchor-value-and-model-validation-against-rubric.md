# exp-da-037 Anchor Value and Model Validation Against Rubric

## Experience
- **Identify all explicit numeric anchors and formula definitions** from the task description or rubric.
- **Before finalizing, compute each anchor via an independent query or calculation** and compare to the expected value.
- **If discrepancies arise, debug** data selection, filters, joins, and aggregation logic step-by-step.
- **For scoring models or new metrics, cross-check results** against known distributions (e.g., segment proportions, overall averages) from the rubric.
- **Document any discrepancies and your reconciliation steps** or justify chosen proxies if direct matches are unavailable.

## Checklist
- Extract all expected anchor numbers and metric definitions from the prompt/rubric
- Run verification queries to recompute these values
- If mismatched, audit data filters, joins, and calculations
- Validate model outputs (e.g., segment sizes) against provided benchmarks
- Note and explain any deviations in the final report

## Common failure prevented
Reporting results that fail to match the grader's expected numeric values or using incorrect metric definitions, leading to accuracy deductions.
