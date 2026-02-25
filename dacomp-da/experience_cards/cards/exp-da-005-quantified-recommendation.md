# exp-da-005 Quantified Recommendation Card

## When to use
- The prompt asks for optimization strategy, governance actions, or execution plan.
- You already identified candidate root causes.
- You need high conclusiveness, not only qualitative suggestions.

## Experience
Translate each recommendation into a measurable control loop:
1. Trigger condition (who/when to apply).
2. Action lever (what to change).
3. Quant target (expected KPI movement and acceptable risk bound).
4. Monitoring window (weekly/bi-weekly) and rollback rule.

## Recommendation template
```text
Action: [specific change]
Applies to: [segment/threshold]
Expected impact (2-6 weeks): [KPI +x%, risk <= y%]
Owner & cadence: [role, weekly checkpoint]
Rollback trigger: [condition]
```

## Common failure prevented
- Advice without measurable target.
- No link between diagnosis and operational execution.
