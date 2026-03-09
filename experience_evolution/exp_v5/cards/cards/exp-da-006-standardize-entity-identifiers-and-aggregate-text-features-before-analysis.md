# exp-da-006 Standardize entity identifiers and aggregate text features before analysis

## Experience
* **Step 1:** Inspect raw text variations by running a frequency count on the field to spot inconsistencies (spelling, abbreviations).
* **Step 2:** Create a mapping dictionary to standardize entity names (e.g., map 'Hongguang MINI EV' and 'Wuling Hongguang MINIEV' to a canonical name).
* **Step 3:** For comma-separated features, split entries, clean whitespace, and map synonyms to a single canonical term.
* **Step 4:** Apply the standardization to create new, clean columns for grouping or counting.
* **Step 5:** Validate the grouping by checking the count of unique groups and sample records within each.
* **Step 6:** Document the standardization logic for reproducibility.

## Checklist
- List unique raw values and spot inconsistencies
- Create and apply a canonical name mapping dictionary
- Split, clean, and deduplicate comma-separated text features
- Verify group counts are sensible after standardization

## Common failure prevented
Incorrect or inconsistent grouping and inflated category counts due to variations in raw text, leading to inaccurate aggregate statistics.
