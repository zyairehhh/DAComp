# exp-da-029 Execute Data Feasibility and Validation Checks

## Experience
*   Verify data availability before defining derived metrics: Immediately check for the existence of all required columns; if a metric is defined but not present, define and justify a proxy.
*   Run targeted queries to confirm the data structure: Count rows and check for NULLs in key metric columns; compute a sample of the main derived metric to verify logic yields sensible results.
*   Anchor numerical outputs to provided benchmarks: Treat explicitly mentioned numbers as anchor points; if results diverge, diagnose the discrepancy before proceeding.
*   Decode and validate embedded data structures first: Profile nested/encoded columns, develop a robust parsing function, and test it on a sample.

## Checklist
- Map required metrics to available columns; define proxies for missing ones
- Confirm key metric columns exist and have plausible non-null values
- Identify and reproduce numerical benchmarks from the task
- Inspect and parse embedded data structures (JSON, key-value) before analysis

## Common failure prevented
Wasting effort on exploration based on incorrect assumptions or missing data, leading to inaccurate metrics that don't match expected benchmarks.
