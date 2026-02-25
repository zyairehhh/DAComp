# exp-da-018 Forecast Uncertainty and Scenario Bands

## When to use
- Task involves forecasting, future cash flow, risk trajectory, or planning under uncertainty.
- Decision quality depends on assumptions and robustness.
- Prior outputs were penalized for single-point estimates without uncertainty handling.

## Experience
Use a scenario-based forecast package instead of one-point prediction:
- Base scenario with stated assumptions.
- Upside/downside scenarios with key driver shifts.
- Sensitivity table showing which assumption moves outcomes most.

Report should include both expected value and risk band, then map decisions to scenario triggers.

## Minimal output
- Scenario table: Scenario, Key Assumptions, Forecast Range, Trigger, Recommended Action.

## Common failure prevented
- Fragile recommendations from deterministic forecasts.
