# exp-da-006 Sensitivity and Robustness Mini-Test

## Experience
Add one compact robustness block before final conclusion:
1. Pick 2-3 key assumptions (e.g., churn, conversion uplift, risk weight).
2. Run base / optimistic / conservative scenarios.
3. Report whether decision ranking changes across scenarios.
4. If ranking flips, provide guardrail rule for safe deployment.

## Output table
- Scenario
- Key assumption changes
- Core KPI/result
- Decision status (stable / flips)

## Common failure prevented
- Single-point recommendation that breaks under small assumption shifts.
