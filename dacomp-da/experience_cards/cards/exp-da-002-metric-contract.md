# exp-da-002 Metric Contract and Threshold Lock

## Experience
Lock metric definitions before segmentation:
1. Create a metric dictionary with exact formula, denominator, unit, and direction.
2. Materialize the target group using those exact rules.
3. Output count + proportion + anchor stats (`min/median/max` or `mean/std`) for quick verification.
4. Reuse the same derived columns everywhere to avoid inconsistent definitions.

## SQL sketch
```sql
WITH base AS (...),
metric AS (
  SELECT
    ...,
    conversion_value * 1.0 / NULLIF(cost, 0) AS roi
  FROM base
),
target AS (
  SELECT * FROM metric WHERE cost > 1000 AND roi < 0.8
)
SELECT
  COUNT(*) AS n_target,
  COUNT(*) * 1.0 / (SELECT COUNT(*) FROM metric) AS pct_target
FROM target;
```

## Common failure prevented
- Using proxy metrics not aligned with prompt definitions.
- Missing denominator or threshold direction mistakes.
