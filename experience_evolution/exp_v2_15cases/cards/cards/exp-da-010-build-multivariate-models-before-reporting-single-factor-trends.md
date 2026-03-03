# exp-da-010 Build multivariate models before reporting single-factor trends

## Experience
- **Explicitly state you will perform multi-factor regression/correlation analysis** before diving into single-factor grouped means.
- **Include modeling steps** in your analysis plan: feature engineering, model fitting, coefficient extraction.
- **Report standardized coefficients and significance** to rank factor importance.
- **Compare multi-factor results with single-factor trends** to check consistency.
- **Use the model to generate predictions or segmentations** (e.g., high-value configurations).

## Checklist
- State intent to build multivariate model
- Engineer features from raw data
- Fit regression/classification model
- Extract and interpret coefficients
- Validate against single-factor trends

## Common failure prevented
Reporting only descriptive grouped means without controlling for confounding variables, leading to incomplete or misleading factor rankings.
