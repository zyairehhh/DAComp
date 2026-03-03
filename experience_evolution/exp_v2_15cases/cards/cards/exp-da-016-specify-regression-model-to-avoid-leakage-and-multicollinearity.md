# exp-da-016 Specify regression model to avoid leakage and multicollinearity

## Experience
To build a robust explanatory regression model:
- **Avoid target leakage**: Ensure predictor variables are not direct mathematical transformations of the target variable or are measured after the outcome is known.
- **Check for multicollinearity**: Before interpreting coefficients, compute Variance Inflation Factors (VIFs) for predictors. If VIF > 5-10, consider removing or combining highly correlated variables.
- **Use logical variable transformations**: Apply transformations like log to skewed variables and include interaction terms where theorized.
- **Validate model specification**: Compare the sign and magnitude of key coefficients with domain expectations. Unrealistically large coefficients often indicate a specification error.
- **Present a clean, interpretable model**: Report coefficients for the most important, non-leaky variables, along with their confidence intervals or p-values.

## Checklist
- Identify and exclude predictors that are direct transformations of the target.
- Calculate VIFs to diagnose and address multicollinearity.
- Apply appropriate transformations to predictors.
- Compare coefficient signs and magnitudes to domain logic.
- Report a final, validated model with key drivers.

## Common failure prevented
This prevents drawing incorrect or unstable conclusions from regression models due to statistical issues like target leakage or multicollinearity.
