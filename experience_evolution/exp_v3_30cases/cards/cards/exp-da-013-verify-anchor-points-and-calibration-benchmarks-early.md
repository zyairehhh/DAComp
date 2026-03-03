# exp-da-013 Verify anchor points and calibration benchmarks early

## Experience
1. **Extract and record explicit anchor points** from the task description or rubric (e.g., 'Video ROAS=3.66').
2. **Compute these anchor values early in your analysis** using the defined logic and data.
3. **Compare your computed values with the provided anchors** to verify your data processing and metric calculations are correct.
4. **If discrepancies exist**, systematically debug: check filtering logic, joins, aggregations, and data cleaning steps.
5. **Only proceed to deeper analysis once anchor points are matched** within an acceptable tolerance.

## Checklist
- Identify required anchor points from task/rubric
- Compute anchor values early
- Compare against provided benchmarks
- Debug discrepancies before proceeding
- Use anchors for calibration

## Common failure prevented
This prevents propagating undetected calculation errors into segmentation and optimization recommendations, ensuring analysis accuracy.
