# exp-da-019 Report both rate and volume for each segment when diagnosing problems

## Experience
- For each segment, compute both the **incidence rate** (e.g., low‑margin rate) and the **absolute volume** (e.g., number of low‑margin orders).
- Sort segments by rate to find the worst‑performing ones.
- Sort segments by volume to find the largest contributors to the total problem.
- Highlight segments that are high in both rate and volume as priority targets.
- In recommendations, distinguish between fixing high‑rate segments (e.g., process overhaul) and high‑volume segments (e.g., scaling proven fixes).

## Checklist
- Calculate low‑margin rate per segment
- Count low‑margin orders per segment
- Identify top segments by rate and top segments by volume
- Flag segments appearing in both lists
- Prioritize recommendations accordingly

## Common failure prevented
Reporting only the rate without noting the volume, missing the biggest impact opportunity.
