# exp-da-010 Denominator and Unit Consistency

## When to use
- The task contains rates, shares, ratios, or weighted averages.
- Multiple tables have similarly named metrics with different denominators.
- Rubrics likely check anchor values tightly.

## Experience
1. Record each metric as formula + denominator + unit (%/ratio/currency/day).
2. For every reported rate, include denominator context in one nearby sentence.
3. Keep one canonical column per metric and reuse it across sections.
4. Before finalizing, run a unit sanity check (0-1 vs 0-100, monthly vs yearly).

## Minimal output
- Metric dictionary with denominator and unit.
- One sample recomputation from raw fields.

## Common failure prevented
- Correct trend with wrong scale or denominator.
