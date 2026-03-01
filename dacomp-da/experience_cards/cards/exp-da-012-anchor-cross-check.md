# exp-da-012 Anchor Number Cross-Check

## Experience
1. For each requirement, pick 2-3 anchor numbers (count/rate/mean/delta).
2. Recompute anchors via an independent query or quick Python check.
3. Report both absolute value and direction (up/down, high/low).
4. If mismatch exists, state cause (filter scope, unit, missing rows) and fix.

## Minimal output
- Anchor check block: metric, expected range, computed value, status.

## Common failure prevented
- Confident conclusions backed by numerically inconsistent tables.
