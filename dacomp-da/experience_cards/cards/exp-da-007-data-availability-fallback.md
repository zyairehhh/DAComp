# exp-da-007 Data Availability and Fallback Protocol

## When to use
- Query results are empty, inconsistent, or database appears corrupted.
- Required tables/columns seem missing.
- You risk spending many steps on broken assumptions.

## Experience
Use a fast diagnostic protocol:
1. Verify file exists and schema list (`sqlite_master`, `PRAGMA table_info`).
2. Validate row counts for required tables.
3. If blocked, explicitly declare what is unavailable and which requirements are impacted.
4. Continue with partial analyses only for requirements that remain valid.

## Minimal checks
```sql
SELECT name FROM sqlite_master WHERE type='table';
SELECT COUNT(*) FROM <critical_table>;
PRAGMA table_info(<critical_table>);
```

## Common failure prevented
- Silent failure leading to fabricated or irrelevant conclusions.
- Wasting steps without producing auditable diagnostics.
