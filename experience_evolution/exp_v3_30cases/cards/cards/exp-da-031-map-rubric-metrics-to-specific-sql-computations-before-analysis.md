# exp-da-031 Map rubric metrics to specific SQL computations before analysis

## Experience
- Before writing any analysis code, parse the rubric to list all required metrics and their exact definitions.
- Write explicit SQL queries or Python functions that compute each metric as defined (e.g., `share_high_disease = COUNT(CASE WHEN disease_risk > threshold THEN 1 END) / COUNT(*)`).
- Validate the computed metrics against sample data to ensure they match rubric logic (e.g., proportions between 0 and 1).
- Include these metric definitions in your documentation or as comments in your code.
- Cross-reference your final results table to confirm it contains all rubric-specified metrics and units.

## Checklist
- List rubric metrics with formulas
- Write SQL for each formula
- Test on sample data
- Verify final table columns match rubric

## Common failure prevented
Producing descriptive statistics that do not satisfy rubric requirements for derived proportion metrics.
