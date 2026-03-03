# exp-da-023 Formally define and calibrate composite scoring systems

## Experience
- **Explicitly list all indicators, their measurement, and directionality** (e.g., profit stability measured by CV of monthly profit, higher is riskier).
- **Assign clear, defensible weights** to each indicator, justifying them based on domain logic or data (e.g., 50% credit rating, 30% profit stability).
- **Validate monotonicity** by testing that the composite score increases/decreases as expected for clear edge cases (e.g., a company with worst rating and worst stability gets highest risk score).
- **Define interval thresholds (e.g., quantiles)** to segment scores into risk categories (e.g., S < 20 = low risk).
- **Document versioning and calibration assumptions** (e.g., random seed, parameter table) to ensure reproducibility.

## Checklist
- List indicators, formulas, and directionality
- Define and justify indicator weights
- Test monotonicity on boundary examples
- Set quantile-based category thresholds
- Document version and calibration assumptions

## Common failure prevented
Prevents building an ad-hoc, untraceable score with implicit weighting that fails rubric validation.
