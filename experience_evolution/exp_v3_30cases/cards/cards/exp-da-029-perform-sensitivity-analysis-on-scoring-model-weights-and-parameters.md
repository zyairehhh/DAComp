# exp-da-029 Perform sensitivity analysis on scoring model weights and parameters

## Experience
* **Identify key tunable parameters:** List all weights, normalization constants (e.g., Z-score baselines), and thresholds in your scoring model.
* **Define perturbation scenarios:** Systematically vary key parameters (e.g., ±10% on dimension weights) and rerun the classification/ranking.
* **Report stability metrics:** For each scenario, calculate the impact—report the proportion of entities whose performance level changes, the Spearman correlation of rankings, or which specific 'top performers' remain stable.
* **Conclude on robustness:** State whether your model's conclusions (especially the classification of 'Excellent' and 'Needs Improvement') are sensitive or robust to reasonable changes in assumptions.

## Checklist
- List all tunable model parameters
- Define weight perturbation scenarios
- Calculate rank/classification stability metrics
- Draw robustness conclusion

## Common failure prevented
Prevents proposing a single scoring model without testing if its outputs are stable, missing required sensitivity checks in the rubric.
