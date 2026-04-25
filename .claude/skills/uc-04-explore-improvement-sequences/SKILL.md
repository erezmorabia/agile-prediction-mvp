---
name: uc-04-explore-improvement-sequences
description: View learned Markov transition patterns between agile practices. Use when modifying the Sequences tab, sequence grouping/display, or the GET /api/sequences response format.
---

# UC-04: Explore Improvement Sequences

## Summary
User browses the Markov chain transition patterns learned from historical data, seeing which practices tend to follow which, and with what frequency and probability.

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with sequences learned at startup (requires ≥ 2 months of any team data)

## Trigger
User clicks the "Sequences" tab.

## Main Flow
1. User clicks Sequences tab → `GET /api/sequences`
2. Page shows sequence stats: total transition types, total transitions observed, number of practices that improved
3. Sequences displayed grouped by "from practice": each entry shows the practice that typically follows with its transition count and probability
4. User can browse to understand organizational patterns (e.g., "CI/CD → Test Automation occurred 12 times with 0.63 probability")

## Alternative / Error Flows
- **No sequences learned** (fewer than 2 consecutive months for any team): stats show zeros; transition list is empty
- **API error:** error message shown on tab

## Cross-references
- **Related Domain Skills:** `/domain-ml` (SequenceMapper, transition matrix, `get_all_sequences()`), `/domain-api` (`GET /api/sequences` handler, `get_improvement_sequences()` service method), `/domain-frontend` (sequences tab rendering)
- **Related Use Case Skills:** `/uc-01-get-recommendations` (sequences contribute 40% of recommendation score), `/uc-05-view-system-statistics` (complementary data overview)
