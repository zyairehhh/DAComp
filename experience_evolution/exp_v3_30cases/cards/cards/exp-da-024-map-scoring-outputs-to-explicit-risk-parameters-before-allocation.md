# exp-da-024 Map scoring outputs to explicit risk parameters before allocation

## Experience
- **Define a mapping function from composite score to PD** (e.g., logistic regression or lookup table), not just historical default rates.
- **Define LGD tiers** based on score intervals or external data, not assume constant LGD.
- **Calculate regulatory capital parameters (K, m, U)** if required by the domain, and incorporate them into limit formulas.
- **Establish explicit bucket-level parameters** (e.g., average PD, LGD, churn, upper/lower limit bounds) before allocation.
- **Perform anchor checks** by verifying that mapping produces sensible PDs for extreme scores (e.g., best score yields near-zero PD).

## Checklist
- Create explicit S→PD mapping function
- Define LGD tiers per risk bucket
- Incorporate regulatory capital parameters if needed
- Document bucket-level parameters (PD, LGD, churn)
- Test mapping on boundary scores

## Common failure prevented
Prevents skipping the formal PD/LGD layering and regulatory capital integration, leading to an incomplete risk-based allocation.
