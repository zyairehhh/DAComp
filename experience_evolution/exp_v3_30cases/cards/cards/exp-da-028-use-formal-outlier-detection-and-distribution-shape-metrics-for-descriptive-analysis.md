# exp-da-028 Use formal outlier detection and distribution shape metrics for descriptive analysis

## Experience
- Beyond mean/median/std, compute skewness and kurtosis (or use |mean−median|/std) to quantify distribution shape. Use thresholds (e.g., |skew| > 1) to label as skewed.
- Identify outliers using the IQR rule (Q1 – 1.5*IQR, Q3 + 1.5*IQR) and list them, noting their impact on summary statistics.
- For each group, report the 95% confidence interval for the mean (using t-distribution) to indicate estimation uncertainty.
- If distribution is highly skewed, consider reporting median and IQR as primary statistics instead of mean/std.

## Checklist
- Compute skewness/kurtosis or |mean-median|/std
- Identify outliers via IQR rule
- Report 95% CI for group means
- Choose appropriate summary stats for skewed data

## Common failure prevented
Providing only basic statistics (mean, median, std) without formal outlier detection, shape quantification, or confidence intervals.
