---
name: uc-05-view-system-statistics
description: System dataset overview: team count, practice count, months, similarity stats, missing values. Use when modifying the Statistics tab, the GET /api/stats response, or practice definition display.
---

# UC-05: View System Statistics

## Summary
User views a snapshot of the loaded dataset: how many teams, practices, and months are included, along with similarity distribution stats and data quality information.

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with data loaded

## Trigger
User clicks the "Statistics" tab.

## Main Flow
1. User clicks Statistics tab → `GET /api/stats`
2. Page shows core dataset figures: number of teams, practices, months, total observations
3. Month list displayed so user can see the date range of the data
4. Similarity statistics shown (mean, std, min, max cosine similarity across all team pairs) — only available after similarity matrix is built
5. Missing values section shows total missing entries, which practices and months are affected
6. Practice definitions panel shows level descriptions (Level 0–3 text) if `practice_level_definitions.xlsx` is present

## Alternative / Error Flows
- **Similarity stats not yet built** (matrix built on first recommendation, not at startup): similarity section shows "not built" state
- **Practice definitions file missing:** definitions panel hidden; stats page still works fully
- **API error:** error message shown on tab

## Cross-references
- **Related Domain Skills:** `/domain-data` (DataProcessor stats, DataValidator missing values), `/domain-api` (`GET /api/stats` handler, `get_system_stats()` service method, PracticeDefinitionsLoader), `/domain-frontend` (statistics tab rendering)
- **Related Use Case Skills:** `/uc-01-get-recommendations` (use stats to understand data before selecting a team), `/uc-04-explore-improvement-sequences` (complementary dataset overview)
