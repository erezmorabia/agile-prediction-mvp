---
name: domain-data
description: Excel loading, 0-3→0-1 normalization, data validation, practice filtering, team_histories dict. Use when modifying data ingestion, normalization, validation logic, or practice definitions loading.
---

# Domain: Data

## Summary
Loads agile metrics from Excel, validates quality, normalizes scores to 0–1, and exposes a `team_histories` dict indexed by team name and month. All downstream ML components read exclusively from this dict.

## Data Flows

- **Load:** `DataLoader.load()` reads sheet 0 of the Excel file → identifies practice columns (all columns except `Team Name` and `Month`) → stores `df`, `practices`, `teams`, `months`
- **Validate + filter:** `DataValidator.validate()` checks required columns and value ranges → `filter_high_missing_practices(practices, threshold=90.0)` removes practices with >90% missing → returns filtered `practices` list used for all subsequent steps
- **Process:** `DataProcessor.process()` fills NaN with 0, divides all practice values by 3.0, then iterates rows to build `team_histories[team_name][month_int] = np.ndarray` (one float per practice, normalized 0–1)
- **Practice definitions (optional):** `PracticeDefinitionsLoader` reads a second Excel file (`practice_level_definitions.xlsx`) to supply level 0–3 text descriptions; loaded by `APIService` at startup; missing file handled gracefully

## Domain Validation Rules and Business Logic

- Required Excel columns: `Team Name` (str), `Month` (int, yyyymmdd format); all other columns treated as practices
- Practice values expected 0–3; NaN filled with 0 before normalization
- Practices with > 90% missing values excluded before model building; `practices` list is mutated in-place in `web_main.py`
- `DataProcessor.process()` modifies the DataFrame in-place (NaN fill + normalization)

## Entity Schemas

**`team_histories`** (produced by `DataProcessor`):
- Type: `dict[str, dict[int, np.ndarray]]`
- Key path: `team_name → month_int → practice_vector`
- `practice_vector`: `np.ndarray` of shape `(n_practices,)`, values 0.0–1.0 (normalized), in column order from original Excel

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `DataLoader.load()` | `src/data/loader.py:27` | `web_main.py` | `file_path` (set at init) → `pd.DataFrame`; sets `self.practices`, `self.teams`, `self.months` |
| `DataLoader.get_team_data()` | `src/data/loader.py:84` | Not used in main path | `team_name` → filtered `DataFrame` |
| `DataValidator.validate()` | `src/data/validator.py` | `web_main.py` | `df, practices` (set at init) → `bool` |
| `DataValidator.filter_high_missing_practices()` | `src/data/validator.py` | `web_main.py` | `practices, threshold=90.0` → `(filtered_practices, excluded_practices)` |
| `DataValidator.get_missing_values_details()` | `src/data/validator.py` | `web_main.py` | → dict with `total_missing`, `by_practice`, `by_month` |
| `DataProcessor.process()` | `src/data/processor.py:27` | `web_main.py` | no args → mutates `self.team_histories`; sets `self.processed = True` |
| `DataProcessor.get_team_history()` | `src/data/processor.py:88` | All ML components | `team_name` → `dict[int, np.ndarray]` |
| `DataProcessor.get_all_teams()` | `src/data/processor.py:106` | All ML components | → `list[str]` |
| `DataProcessor.get_all_months()` | `src/data/processor.py:112` | All ML components | → sorted `list[int]` |
| `PracticeDefinitionsLoader` | `src/data/practice_definitions.py` | `APIService.__init__()` | loads level descriptions; `get_definitions()` → `dict[str, dict]` |

## Cross-references
- **Related Use Case Skills:** `/uc-05-view-system-statistics` (missing values and practice counts surface here)
- **Related Domain Skills:** `/domain-ml` (consumes `DataProcessor`), `/domain-validation` (consumes `DataProcessor`), `/domain-api` (APIService loads practice definitions)
