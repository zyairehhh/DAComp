# exp-da-014 Summarize data granularity and aggregation strategy before analysis

## Experience
1. **Determine the reporting grain of the primary data table** (e.g., is the data at the daily ad_group level, or at the keyword level?).
2. **Identify the final entity level required for the analysis** (e.g., the task asks for 'problematic ad groups' – the final level is `ad_group`).
3. **Plan the necessary aggregation steps** to get from the raw grain to the required entity level.
4. **Calculate derived metrics (ratios, rates) only after aggregating the raw counts** to the correct level.
5. **Check for data completeness** at the desired aggregation level.

## Checklist
- Identify raw grain
- Identify final entity level
- Plan aggregation of raw counts
- Calculate metrics after aggregation
- Check data completeness

## Common failure prevented
Calculating metrics at the wrong granularity (e.g., daily) and then aggregating them, which can produce mathematically incorrect averages of ratios.
