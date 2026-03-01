# exp-da-020 Data Prerequisite Gate and Parsing

## Experience
Before any analysis, verify that required data subsets and fields exist and are correctly parsed:
1. Run `SELECT name FROM sqlite_master WHERE type='table';` to list all tables.
2. For each critical table: `PRAGMA table_info(<table>);` and `SELECT COUNT(*) FROM <table>;`
3. If task requires specific record types (e.g., "single-item promotions", "direct markdown"), filter and verify that the subset is non-empty before proceeding.
4. For nested/embedded data (JSON fields, serialized columns): parse first, validate row count after expansion, then proceed with analysis.
5. If a prerequisite filter yields zero rows, do NOT fabricate analysis -- explicitly state what's missing and adjust the approach.

## Prerequisite check template
```sql
-- Step 1: Verify tables exist
SELECT name FROM sqlite_master WHERE type='table';

-- Step 2: Check critical table schema and size
PRAGMA table_info(<critical_table>);
SELECT COUNT(*) FROM <critical_table>;

-- Step 3: Verify prerequisite subset is non-empty
SELECT COUNT(*) FROM <table> WHERE <prerequisite_condition>;
```

## Common failure prevented
- Entire analysis built on wrong data subset (scoring 0 on all rubric items).
- Nested/embedded data not parsed, leading to missing or fabricated results.
