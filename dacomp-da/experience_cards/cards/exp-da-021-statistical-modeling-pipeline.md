# exp-da-021 Statistical Modeling Pipeline

## Experience
When the task requires building scoring models, regression analysis, or predictive frameworks:
1. Define the target variable and feature set explicitly before modeling.
2. For regression: use standardized features, report coefficients with direction and significance, check R-squared.
3. For scoring models: define the score range (e.g., 0-100), normalization method, and weighting rationale.
4. For classification: handle class imbalance, report precision/recall/AUC, use cross-validation.
5. Always validate with at least one independent check: holdout set, cross-validation, or bootstrap.

## Modeling checklist
```text
1. Target variable: [definition, distribution check]
2. Features: [list, missing rate, correlation with target]
3. Method: [chosen model, why this method]
4. Validation: [cross-validation, holdout, or bootstrap]
5. Key outputs: [coefficients/importance, R²/AUC, anchor values]
6. Interpretation: [business meaning of top features]
```

## Common failure prevented
- Model built without validation, leading to unreliable coefficients.
- Scoring model without clear normalization, producing uninterpretable results.
- Missing feature importance ranking or directional interpretation.
