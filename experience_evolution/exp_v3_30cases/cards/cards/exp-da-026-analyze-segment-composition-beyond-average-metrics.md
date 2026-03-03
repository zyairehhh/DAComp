# exp-da-026 Analyze segment composition beyond average metrics

## Experience
- **Examine the distribution of key categorical or binary flags within the segment** (e.g., % of orders with Sales Quantity = 1, % from a specific region).
- **Compare the segment's composition to the overall population's composition** to identify over/under-representation.
- **Report both the rate (e.g., proportion) and volume (e.g., count) of key sub-segments** to understand business impact.
- **Avoid stopping at average values for numeric fields**; also check for modal values, common categories, or extreme values that define the segment.

## Checklist
- Identify key binary/categorical flags relevant to the business context (e.g., 'retail customer', 'remote region').
- Calculate the proportion of the target segment that belongs to each flag.
- Calculate the same proportion for the overall population or a comparison group.
- Report both the segment rate and the count of affected items.
- Highlight flags where the segment's composition differs significantly from the norm.

## Common failure prevented
Missing that a segment is primarily defined by a specific categorical characteristic (e.g., retail customers) because analysis focused only on average numeric metrics.
