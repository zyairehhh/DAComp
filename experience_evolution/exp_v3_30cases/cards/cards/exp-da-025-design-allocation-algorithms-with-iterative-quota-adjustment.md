# exp-da-025 Design allocation algorithms with iterative quota adjustment

## Experience
- **Define per-entity initial limits** based on capacity score and risk-adjusted return.
- **Specify per-bucket caps and floors** (e.g., max exposure per rating, minimum limit).
- **Implement an iterative scaling algorithm** (e.g., while total allocated > total available, reduce limits proportionally; while total < available, increase up to caps).
- **Log intermediate quantities** (e.g., initial allocation, adjustments, final limits) for transparency and debugging.
- **Test convergence and boundary cases** (e.g., all entities hit caps, one entity dominates capacity).

## Checklist
- Define initial limit formula per entity
- Set per-bucket caps/floors
- Write pseudocode for iterative scaling
- Log intermediate allocation steps
- Test extreme scenarios for convergence

## Common failure prevented
Prevents a simplistic one-shot proportional allocation that ignores constraints, leading to unrealistic or infeasible limits.
