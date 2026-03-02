# exp-da-028 Standardize Text Fields Before Aggregation

## Experience
*   Pre-process for consistency: Clean whitespace, punctuation, and case variations before splitting and counting.
*   Consolidate synonyms and near-duplicates: Manually review high-frequency terms to merge equivalents (e.g., 'high-temperature allowance' and 'high temperature allowance').
*   Validate against a known schema if possible: If a standard list exists, map extracted terms to it.
*   Report both raw and standardized counts: This transparency helps identify preprocessing impact.

## Checklist
- Strip and lowercase all terms
- Create a synonym mapping table
- Aggregate counts after mapping
- Report pre/post standardization totals

## Common failure prevented
Inaccurate frequency distributions due to multiple representations of the same item.
