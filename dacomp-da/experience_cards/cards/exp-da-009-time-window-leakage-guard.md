# exp-da-009 Time Window and Leakage Guard

## Experience
1. Define explicit window boundaries first (train/observe vs evaluate/target).
2. Build features only from the past window; never reference future rows.
3. Report entity counts per window (users/projects/accounts) to prove validity.
4. Add one leakage check statement in report: "all features are computed before target window".

## Minimal output
- Window definition table.
- Per-window sample count and coverage rate.
- One leakage audit sentence.

## Common failure prevented
- Hidden data leakage and invalidly high conclusions.
