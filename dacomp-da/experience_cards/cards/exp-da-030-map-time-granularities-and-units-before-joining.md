# exp-da-030 Map Time Granularities and Units Before Joining

## Experience
*   Identify all time columns and units in relevant tables before any joins.
*   Create and document a mapping formula or logic to align granularities (e.g., aggregate monthly to quarterly).
*   Verify the mapping by spot-checking a few records to ensure data aligns correctly.
*   If mapping creates missing values, establish and state a clear imputation policy.
*   In the final report, list which time unit each metric is aggregated to and justify the choice.

## Checklist
- List all time columns and units
- Define mapping/aggregation logic
- Validate mapping with sample records
- Set imputation policy for missing mapped data
- Document time unit for each output metric

## Common failure prevented
Joining data incorrectly across time periods, which skews computed metrics and breaks anchor expectations.
