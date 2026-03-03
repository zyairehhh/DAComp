# exp-da-020 Design and test allocation algorithms with explicit constraints and invariants

## Experience
- Define the allocation as a multi-step chain (e.g., base amount → adjustment factors → final amount), ensuring each step's formula is clear.
- Specify all constraints: total budget cap, per-entity minimum/maximum, concentration limits, and monotonicity rules (e.g., risk↑ → limit↓).
- Develop an iterative scaling algorithm if needed to meet the total budget exactly, and document its pseudocode.
- Perform boundary tests: apply the algorithm to extreme cases (e.g., all entities identical, one entity dominates) to check for robustness and fairness.
- Provide a worked example tracing the calculation for 2-3 sample entities from raw data to final allocation.

## Checklist
- Define allocation chain with intermediate quantities
- List all constraints and invariants
- Provide iterative algorithm if needed
- Test with boundary/edge cases
- Show sample calculation trace

## Common failure prevented
Proposing proportional allocation formulas without ensuring they satisfy total budget constraints, concentration rules, or risk monotonicity.
