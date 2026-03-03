# exp-da-021 Map rubric sub-criteria to analysis outputs before coding

## Experience
- Extract all specific sub-criteria (e.g., formulas, required tables, significance tests) from the rubric before writing any code.
- Create a checklist mapping each sub-criterion to a planned output (e.g., '1.2.A.1 requires computing share_high_disease per level; define formula').
- Validate that all required metrics, units, and annotations (e.g., p-values, confidence intervals) are explicitly planned.
- Before finalizing, cross-check each analysis output against the rubric checklist to ensure all items are addressed.
- If a rubric criterion involves multiple steps (e.g., winsorization, anomaly handling), implement and report each step separately.

## Checklist
- Parse rubric into sub-criteria list
- Map each sub-criterion to a specific analysis component
- Verify required outputs (tables, formulas, tests) are planned
- Implement and report each step explicitly
- Cross-check final report against rubric

## Common failure prevented
Missing required analysis components because the agent dove into exploratory coding without aligning with the rubric.
