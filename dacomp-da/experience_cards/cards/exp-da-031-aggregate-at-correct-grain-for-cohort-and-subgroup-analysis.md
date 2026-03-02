# exp-da-031 Aggregate at Correct Grain for Cohort and Subgroup Analysis

## Experience
*   Determine the primary unit of analysis (e.g., ad_group, campaign) and ensure all aggregations (SUM, AVG) are performed at that level before filtering.
*   For rate calculations, aggregate the numerator and denominator separately at the unit level before division.
*   First, isolate the target entity list (e.g., problematic campaigns), then compute subgroup metrics only within that list.
*   Apply percentile filters or comparisons on the aggregated, per-unit metrics, not on raw row-level data.
*   Explicitly compare the target subgroup's metrics to the overall population or a control group to highlight differences.

## Checklist
- Confirm the unit of analysis (e.g., ad group, campaign)
- Aggregate performance sums and calculate derived rates per unit
- Define target entity list for subgroup analysis
- Compute percentiles and apply filters on per-unit metrics
- Compare subgroup metrics to baseline or control group

## Common failure prevented
Incorrect cohort identification or reporting overall population trends instead of the specific problematic cohort by applying filters to the wrong aggregation level.
