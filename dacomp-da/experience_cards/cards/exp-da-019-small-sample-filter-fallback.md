# exp-da-019 Small-Sample Filter Fallback

## When to use
- Strict filtering (top percentile, high-priority slice, threshold lock) yields tiny sample or unstable metrics.
- Task still requires conclusions and recommendations.
- Prior runs collapsed to near-empty outputs after filtering.

## Experience
Apply a fallback protocol when sample size is too small:
- Keep strict cohort as primary view.
- Add one adjacent cohort (relaxed threshold or nearest quantile bucket) for stability reference.
- Flag confidence and avoid overconfident recommendations on unstable estimates.

Always separate "strict finding" vs "stability reference" to avoid denominator confusion.

## Minimal output
- Cohort stability block: strict N, fallback N, key metric deltas, confidence level.

## Common failure prevented
- Zero/near-zero evidence pipelines and unreliable conclusions.
