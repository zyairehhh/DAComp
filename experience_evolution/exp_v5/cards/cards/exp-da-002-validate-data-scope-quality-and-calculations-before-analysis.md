# exp-da-002 Validate data scope, quality, and calculations before analysis

## Experience
* **Step 1:** Explicitly verify filter logic (e.g., for 'Completed' rides) by checking record counts and a sample of filtered rows.
* **Step 2:** For derived metrics, check for division-by-zero errors, negative/implausible values, and extreme outliers.
* **Step 3:** Verify data availability for all required fields and confirm the dataset contains sufficient data for planned segments (e.g., sample size per group).
* **Step 4:** For time-series or multi-table analyses, verify time granularity consistency and mapping logic between tables.
* **Step 5:** Document any data limitations, assumptions (e.g., imputation for missing periods), and how they might affect conclusions.

## Checklist
- Verify filter logic with a sample check
- Sanity-check derived metrics for extreme values
- Check sample sizes per segment before aggregating
- Confirm data availability for all required fields and time periods

## Common failure prevented
Drawing conclusions from incomplete, erroneous, or mis-aggregated calculations due to uncaught data quality or scope issues.
