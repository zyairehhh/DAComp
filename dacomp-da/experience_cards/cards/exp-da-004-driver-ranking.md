# exp-da-004 Driver Ranking with Consistency Checks

## Experience
Rank drivers using a lightweight but defensible stack:
1. Pairwise association (correlation or effect-size by bins).
2. Controlled model (simple regression with standardized features).
3. Extreme-group delta (top vs bottom quantiles on outcome).
4. Keep only factors whose direction is consistent across at least two methods.

## Output contract
For each retained driver:
- direction (`+` or `-`)
- effect evidence (coef/corr/delta)
- operational interpretation (what to change)

## Common failure prevented
- Picking "strongest driver" from a single correlation table.
- Contradictory conclusions from different analyses.
