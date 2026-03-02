# exp-da-035 Define and Expand Cohorts via Comprehensive Text Search

## Experience
- **Map the cohort definition** to all possible labels, synonyms, and column names in the data.
- **Search across all relevant text fields** using `LIKE` or regex patterns, not just a single categorical column.
- **Union results from multiple search strategies** (exact match, keyword, description field) and deduplicate.
- **Validate the final cohort size** for reasonableness and report the filtering logic and sample count.
- **Standardize extracted text lists** (e.g., comma-separated benefits) by cleaning, splitting, and mapping synonyms before aggregation.

## Checklist
- List all possible labels/synonyms for the target cohort
- Search primary and secondary text columns for matches
- Combine results from different search methods
- Standardize and clean extracted list items before counting
- Report final cohort size and method

## Common failure prevented
Missing a large portion of the target population due to relying on a single column, leading to biased analysis and incorrect sample sizes.
