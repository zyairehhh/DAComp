# exp-da-006 Aggregate data at the correct entity level before computing ratios

## Experience
- Confirm the primary unit of analysis from the task (e.g., aggregate by `ad_group_id`).
- Determine the time granularity: sum additive metrics (clicks, impressions) across the relevant date range.
- Write a query that sums absolute measures grouped by the entity, then compute derived ratios from the aggregated sums, not from pre-averaged daily values.
- Ensure your `GROUP BY` includes all necessary identifier columns.
- Validate aggregation logic by comparing a sample entity's raw daily totals with the aggregated result.

## Checklist
- Determine the correct entity level from the task description
- Decide on time aggregation (sum across dates unless specified)
- Sum absolute measures (clicks, impressions) grouped by the entity
- Compute derived ratios from the aggregated sums, not from averages of averages
- Test aggregation by comparing a sample's raw and aggregated totals

## Common failure prevented
Prevents inaccurate metrics by incorrectly averaging daily ratios instead of summing raw counts before calculating ratios.
