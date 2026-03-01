# exp-da-013 Missing Value and Imputation Policy

## Experience
1. Quantify missingness first (missing count and share).
2. Apply a declared policy: drop / fill constant / group median / fallback source.
3. Justify policy briefly with business impact.
4. Add one sensitivity line: "main conclusion unchanged under alternative fill" (if tested).

## Minimal output
- Missingness summary table and chosen imputation rule.

## Common failure prevented
- Silent NaN propagation and unstable metric outputs.
