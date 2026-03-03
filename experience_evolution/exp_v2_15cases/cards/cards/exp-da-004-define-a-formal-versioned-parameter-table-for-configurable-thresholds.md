# exp-da-004 Define a formal, versioned parameter table for configurable thresholds

## Experience
- Create a structured, documented parameter table (e.g., `risk_thresholds_v1`) listing each indicator, its bounds, risk level, source, and version.
- Document unit conversion and harmonization rules.
- Implement logic that references this table, allowing thresholds to be easily updated or swapped.
- In your outputs, include traceability fields (e.g., `triggered_threshold`, `threshold_source`) to document tagging decisions.

## Checklist
- Create a structured, documented threshold table with source and version
- Define risk levels (e.g., Green/Yellow/Red) for each indicator
- Implement code that references the table, not hard-coded values
- Include traceability fields for tagging decisions in outputs

## Common failure prevented
Prevents non-reproducible, untraceable analysis by formalizing threshold management, meeting structured rubric requirements.
