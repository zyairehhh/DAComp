# Seed Cases for Experience Extraction

These cards were seeded from low-performing baseline cases to capture reusable failure modes.

## Selected baseline cases
- `dacomp-058` (very low score): missing required preprocessing contracts (quarter mapping, avg_position fallback), incomplete business red-line verification.
- `dacomp-060`: incomplete decomposition dimensions and missing anchor calculations (CPC/CPA/IMR/landing-page checks).
- `dacomp-069`: weak metric dictionary/time-window verification, no weighted aggregation despite requirement.
- `dacomp-078`: missing explicit past/future windows and leakage-safe setup.
- `dacomp-081`: failed parsing/field retention protocol and unstable segmentation validation.

## Reusable error families extracted
- Requirement coverage leakage (some required outputs omitted).
- Metric-definition drift (wrong formula or threshold usage).
- One-view diagnosis (no target/control/quantile triangulation).
- Driver claims without multi-method consistency checks.
- Recommendations not quantified into operational loops.
- Missing robustness/scenario checks for policy decisions.
- Inadequate data-availability diagnostics when source quality is weak.

## Cards mapped to these families
- `exp-da-001` Requirement Coverage Matrix
- `exp-da-002` Metric Contract and Threshold Lock
- `exp-da-003` Segmentation Triad
- `exp-da-004` Driver Ranking with Consistency Checks
- `exp-da-005` Quantified Recommendation Card
- `exp-da-006` Sensitivity and Robustness Mini-Test
- `exp-da-007` Data Availability and Fallback Protocol
- `exp-da-008` Final Report Hardening Checklist

## v2 Extensions (Rubric-alignment hardening)
- `exp-da-009` Time Window and Leakage Guard
- `exp-da-010` Denominator and Unit Consistency
- `exp-da-011` Path Minimum Output Contract
- `exp-da-012` Anchor Number Cross-Check
- `exp-da-013` Missing Value and Imputation Policy
- `exp-da-014` Claim-Evidence Linking

## v3 Extensions (Regression hardening for degraded cases)
- `exp-da-015` Strategy Roadmap Operationalization
- `exp-da-016` Causal Claim Countercheck
- `exp-da-017` Requirement Coverage Ledger
- `exp-da-018` Forecast Uncertainty and Scenario Bands
- `exp-da-019` Small-Sample Filter Fallback
