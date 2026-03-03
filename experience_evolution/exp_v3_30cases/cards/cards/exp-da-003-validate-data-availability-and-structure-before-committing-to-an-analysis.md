# exp-da-003 Validate data availability and structure before committing to an analysis

## Experience
- Perform systematic data profiling: check for missing values, data types, unique values, and basic distributions for all key columns.
- Verify that columns needed for planned analyses contain valid, non-null data in sufficient volume.
- Test a small, representative query for each major planned analysis to confirm the data supports it.
- If data issues are found (e.g., many nulls, incorrect types), adjust the analysis plan immediately—don't proceed with assumptions.
- Document data limitations and how they affect the analysis scope and confidence in results.

## Checklist
- Profile key columns (missing, types, distributions)
- Test queries for each planned analysis
- Adjust plan based on data quality findings
- Document data limitations and their impact

## Common failure prevented
Prevents wasted effort on analyses that fail due to unexpected data issues and ensures the plan adapts to the actual data.
