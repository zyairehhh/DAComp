# exp-da-034 Validate Data Prerequisites and Feasibility Before Analysis

## Experience
- **Explicitly list data prerequisites** (tables, columns, filters) required for each rubric requirement before writing code.
- **Run immediate validation queries** (e.g., `SELECT COUNT(*)`, sample rows) to confirm data accessibility, schema, and non-null values.
- **Follow a time-bound escalation** for data access issues (e.g., 5-10 minutes); if unresolved, document the issue and stop rather than using synthetic data.
- **Map each analysis requirement to its specific data source** and confirm the required subset exists (e.g., filtered promotion records).
- **Document prerequisite status** and any fallback decisions in the final report.

## Checklist
- List required data elements for each rubric item
- Execute simple validation queries to confirm data exists and is usable
- Set a time limit for troubleshooting data access failures
- If prerequisites are unmet, stop analysis and document the issue
- Log data source mappings for all requirements

## Common failure prevented
Scoring zero on rubric sections because analysis proceeded on missing, corrupted, or incorrect data.
