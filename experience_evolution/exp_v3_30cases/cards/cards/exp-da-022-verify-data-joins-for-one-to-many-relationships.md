# exp-da-022 Verify data joins for one-to-many relationships

## Experience
- Before joining, run `COUNT(DISTINCT key)` and `COUNT(*)` on each table to check for duplicate key values.
- Decide the correct grain for your analysis (e.g., per customer, per order). If a table has multiple rows per key, aggregate it to that grain first or use a DISTINCT subset of attributes.
- After joining, verify the row count matches expectations. Check for inflation (cartesian products) or loss of records.
- Note any assumptions made about data relationships (e.g., 'using the first recorded profile per customer') in your analysis log.

## Checklist
- What is the grain (level) of my final analysis table?
- Do the keys I'm joining on have a one-to-one or one-to-many relationship?
- Have I aggregated or deduplicated data to the correct grain before joining?
- Does the post-join row count make sense given the pre-join counts?

## Common failure prevented
Incorrectly joining data that has multiple rows per key, leading to inflated metrics and inaccurate segment-level calculations.
