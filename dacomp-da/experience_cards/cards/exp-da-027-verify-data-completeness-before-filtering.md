# exp-da-027 Verify Data Completeness Before Filtering

## Experience
*   Cross-reference multiple identification methods: Don't rely solely on one column; also search for related keywords in descriptive text fields.
*   Validate filter logic with a reference count: Check if your filtered count is plausible relative to the dataset size or a known estimate.
*   Explicitly document inclusion/exclusion criteria: State which columns and keywords were used to define the target cohort for reproducibility.

## Checklist
- Search all text columns for cohort-defining keywords
- Compare filtered count to dataset size for plausibility
- Log the exact filter logic used

## Common failure prevented
Missing a significant portion of the target population by using only one data source.
