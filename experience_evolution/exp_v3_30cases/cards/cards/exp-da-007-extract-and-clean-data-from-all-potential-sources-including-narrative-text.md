# exp-da-007 Extract and clean data from all potential sources including narrative text

## Experience
- Identify all potential data sources, including structured columns and unstructured text columns like 'Job Description' or 'Remarks'.
- Construct keyword lists and use pattern matching (LIKE, regex) on text columns to find all relevant mentions.
- Combine results from both structured and unstructured sources before counting or summarizing to avoid significant undercounting.
- After extraction, inspect raw values for spelling differences and synonyms, then apply standardization rules (lowercasing, removing punctuation) before aggregation.
- Cross-check total counts with domain expectations or sample manual verification to validate completeness.

## Checklist
- List all relevant columns, including long text fields
- Design keyword or pattern searches for each required entity in text fields
- Merge results from structured and unstructured sources
- Standardize extracted categorical values before aggregation
- Compare total counts to a sanity check or benchmark

## Common failure prevented
Prevents missing a large portion of relevant records by ignoring information stored only in descriptive text fields and prevents fragmented counts from inconsistent formatting.
