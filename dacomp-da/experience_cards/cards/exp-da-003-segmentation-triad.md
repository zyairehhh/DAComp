# exp-da-003 Segmentation Triad (Target vs Control vs Quantiles)

## When to use
- The task asks why a high-score or high-cost group underperforms.
- You need diagnosis rather than only ranking.
- There is risk of confounding between structure and execution.

## Experience
Use three complementary cuts to avoid one-sided conclusions:
1. **Target vs Control**: compare flagged group against rest.
2. **Within-target quantiles**: split target by outcome quartiles to detect internal drivers.
3. **Cross-segment check**: at least one orthogonal segmentation (region/device/channel/team size).

For each cut, report the same KPI panel for comparability.

## KPI panel baseline
- Scale: `count`, `% of total`
- Outcome: primary KPI (`conversion`, `completion`, `margin`)
- Process: schedule/quality/velocity related metric
- Risk: volatility/overdue/churn or analogous risk metric

## Common failure prevented
- Declaring root cause from a single comparison view.
- Missing internal heterogeneity inside the target cohort.
