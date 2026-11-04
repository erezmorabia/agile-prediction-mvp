---
name: uc-04-explore-improvement-sequences
description: View learned empirical practice-transition patterns between consecutive improvement-bearing steps. Use when modifying the Sequences tab, sequence grouping/display, or the GET /api/sequences response format.
---

# UC-04: Explore Improvement Sequences

## Summary
User browses empirical transition patterns learned from historical data, seeing which practices tend to follow which, with counts and shares of outgoing transitions.

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with sequences learned at startup (requires ≥ 2 months of any team data)

## Trigger
User clicks the "Sequences" tab.

## Main Flow
1. User clicks Sequences tab → `GET /api/sequences`
2. Page shows sequence stats: total transition types, total transitions observed, number of practices that improved
3. Sequences are grouped under “After [source practice] improved → what improved next?”, with a summary of distinct next practices and total observed transitions. Each expanded group explains that the next step is within the same team and displays a table: Next practice / Observed transitions / Share of transitions.
4. Shares divide each pair count by all outgoing transition counts from its source; several practices improving in the next step each create a transition. No average probability is shown.
5. The page explains that recommendations blend similar-team behavior, transitions, and time-aware popularity with weights selected per prediction month using previously completed outcomes, without a fixed transition percentage.

## Alternative / Error Flows
- **No sequences learned** (fewer than 2 consecutive months for any team): stats show zeros; transition list is empty
- **API error:** error message shown on tab

## Cross-references
- **Related Domain Skills:** `/domain-ml` (SequenceMapper, transition matrix, `get_all_sequences()`), `/domain-api` (`GET /api/sequences` handler, `get_improvement_sequences()` service method), `/domain-frontend` (sequences tab rendering)
- **Related Use Case Skills:** `/uc-01-get-recommendations` (sequence evidence is one input to the monthly selected blend), `/uc-05-view-system-statistics` (complementary data overview)
