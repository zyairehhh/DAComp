# Experience Card Test Plan (Representative Subset)

## Goal
Evaluate whether experience retrieval improves DAComp-DA scores relative to baseline while minimizing run cost.

## Recommended representative set (8 cases)
- `dacomp-058` (index 57): threshold contract + missing/imputation + multi-dimensional diagnosis + recommendations.
- `dacomp-060` (index 59): CTR-high/CVR-low mismatch, segmentation and recommendation quantification.
- `dacomp-069` (index 68): metric definition consistency and weighted comparison integrity.
- `dacomp-070` (index 69): non-linear relationships and driver ranking consistency.
- `dacomp-074` (index 73): forecasting/assumption-sensitive analysis.
- `dacomp-078` (index 77): time-window definition and leakage guard.
- `dacomp-081` (index 80): parsing/availability fallback and strict completeness checks.
- `dacomp-092` (index 91): quantile threshold + anchor number verification.

`example_index`: `57,59,68,69,73,77,80,91`

## Fast smoke set (5 cases)
- `dacomp-058`, `dacomp-060`, `dacomp-069`, `dacomp-078`, `dacomp-081`

`example_index`: `57,59,68,77,80`

## Regression set (12 cases, recommended after card updates)
- Gain-sensitive: `dacomp-058`, `dacomp-060`, `dacomp-070`, `dacomp-029`, `dacomp-080`, `dacomp-081`
- Risk-sensitive: `dacomp-067`, `dacomp-027`, `dacomp-017`, `dacomp-074`, `dacomp-069`, `dacomp-098`

`example_index`: `57,59,69,28,79,80,66,26,16,73,68,97`

## Why this subset is representative
- Covers low-baseline and medium-baseline failure modes.
- Covers the dominant rubric risks: completeness leakage, metric precision, path output completeness, and conclusion evidence linkage.
- Covers both structured KPI tasks and open-ended diagnosis/recommendation tasks.
