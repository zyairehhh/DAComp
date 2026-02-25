# exp-da-013 Missing Value and Imputation Policy

## When to use
- Required metrics come from joins where columns may be missing (for example avg_position).
- The prompt/rubric implies a default fill value or fallback logic.
- Different imputations materially change ranking or risk levels.

## Experience
1. Quantify missingness first (missing count and share).
2. Apply a declared policy: drop / fill constant / group median / fallback source.
3. Justify policy briefly with business impact.
4. Add one sensitivity line: "main conclusion unchanged under alternative fill" (if tested).

## Minimal output
- Missingness summary table and chosen imputation rule.

## Common failure prevented
- Silent NaN propagation and unstable metric outputs.
