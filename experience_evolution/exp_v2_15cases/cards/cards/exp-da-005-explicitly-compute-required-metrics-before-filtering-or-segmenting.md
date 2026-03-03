# exp-da-005 Explicitly compute required metrics before filtering or segmenting

## Experience
- Write a query that clearly calculates the core derived metrics (e.g., CTR, CVR) for all relevant entities.
- Calculate the global threshold values (e.g., 75th percentile, overall average) from the derived metrics in a separate step.
- Apply the thresholds to filter or segment the entities, ensuring the logic aligns exactly with the task's criteria.
- Account for edge cases like NULL or zero values in denominators to avoid calculation errors.
- Validate the filtered set by spot-checking a few records against the raw data.

## Checklist
- Compute all required derived metrics in a CTE or subquery
- Calculate percentile or average thresholds in a separate step
- Join the derived metrics with the thresholds and apply the correct filter logic
- Include NULL/zero handling for safe division
- Spot-check results against raw data for verification

## Common failure prevented
Prevents incorrect segmentation (e.g., percentile-based) due to incorrectly sequenced or missing calculations.
