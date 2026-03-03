# exp-da-012 Standardize free-text entries into a controlled vocabulary

## Experience
1. **After initial extraction of items** (e.g., benefits, skills, entity names), manually review the top N most frequent raw entries to identify synonyms and variations.
2. **Create a mapping dictionary** to consolidate these variations into a standard, canonical term.
3. **Apply this mapping to all extracted data** before calculating final frequencies or distributions.
4. **When reporting, present the consolidated distribution** and optionally note the original variations that were merged.

## Checklist
- Review top raw entries for synonyms
- Create a synonym mapping dictionary
- Apply mapping to standardize categories
- Report consolidated distribution

## Common failure prevented
Inaccurately splitting counts for the same real-world concept due to minor textual differences, leading to an unreliable distribution.
