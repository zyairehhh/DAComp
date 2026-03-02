# exp-da-023 Definition Lock

## Experience
When the task defines a metric, formula, or cohort (e.g. "conversion rate = X/Y", "top 10% by revenue"), use that exact definition and state it in the report.
1. Copy or paraphrase the task’s definition once in the report (e.g. in a "Definitions" or "Methods" subsection).
2. Implement the same definition in SQL/code (same numerator, denominator, filters).
3. If the task gives a threshold (e.g. "exceeding 50%"), check your computed values against it and report pass/fail or counts.
4. Do not substitute a different metric (e.g. "approximate conversion" when the task asks for a specific formula).

## Checklist
- Task definition of key metrics → written in report and used in code.
- Any "top N", "above X", "below Y" → explicit filter in query and stated in text.

## Common failure prevented
- Accuracy deductions for using a different definition than the task.
- Wrong cohort or threshold leading to irrelevant or unscored results.
