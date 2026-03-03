# exp-da-015 Decompose performance change into mix and rate effects

## Experience
- **Define the aggregate metric** (e.g., overall conversion rate) as a weighted average of segment-level rates, where weights are the segment's share of a base.
- **Calculate the mix effect** by holding segment rates constant and recalculating the aggregate using changed segment weights. This isolates the impact of shifting volume between segments.
- **Calculate the rate effect** by holding segment weights constant and applying changed segment rates. This isolates the impact of performance changes within segments.
- **Sum the mix and rate effects** and verify they equal the total observed change in the aggregate metric.
- **Present results** to explain whether the overall change is driven more by shifting volume (mix) or by changes in segment-specific performance (rate).

## Checklist
- Calculate segment-level rates and weights for each time period.
- Hold rates constant, recalculate aggregate with new weights to compute mix effect.
- Hold weights constant, recalculate aggregate with new rates to compute rate effect.
- Verify mix + rate effect equals total change.
- Conclude which effect is the primary driver.

## Common failure prevented
This prevents missing the structural drivers of an aggregate change, such as attributing a drop entirely to performance declines when it could be due to a shift in volume to lower-performing segments.
