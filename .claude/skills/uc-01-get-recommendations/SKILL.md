---
name: uc-01-get-recommendations
description: Team + month selection → top N practice recommendations with scores, explanations, and validation. Use when modifying the recommendations tab, request/response flow, or how results are rendered.
---

# UC-01: Get Recommendations

## Summary
User selects a team and a prediction month; the system returns the top N recommended practices to improve, each with a confidence score, current maturity level, explanation, and validation against actual historical improvements.

## Actor & Preconditions
- **Actor:** Analyst (any user of the web UI)
- **Preconditions:** Server running with data loaded; target team exists with ≥ 2 months of history; selected month is globally month 3 or later

## Trigger
User opens the Recommendations tab (default on page load), selects a team from the dropdown, selects a prediction month, and clicks "Get Recommendations".

## Main Flow
1. Page loads → `GET /api/teams` populates the team dropdown (teams sorted by number of months, most history first)
2. User selects a team → `GET /api/teams/{team_name}/months` populates the month dropdown with valid prediction months (month 3+ only, team must have a prior month)
3. "Get Recommendations" button enables once both selections are made
4. User clicks button → `POST /api/recommendations` with `{ team, month, top_n, k_similar }`
5. Response returns a recommendations list (practice name, score, current level, explanation, similar_teams list, validated flag)
6. UI renders each recommendation as a card: practice name, score bar, current maturity level, "why" text (e.g., "3 similar teams improved this + sequence patterns")
7. Practice profile panel shows all practices grouped into Level 0–3 maturity buckets
8. Validation panel shows what actually improved in the predicted month and up to 2 months ahead, with hit/miss indicators on each recommendation card

## Alternative / Error Flows
- **Team has no valid prediction months:** month dropdown stays empty; button stays disabled
- **API returns error 400:** error message displayed inline (e.g., "No similar teams found for this selection")
- **No improvements in validation window:** validation panel shows "No improvements recorded" — this is not a model failure
- **Score = None (accuracy):** shown as "—" rather than a percentage when no improvements occurred in the window

## Cross-references
- **Related Domain Skills:** `/domain-ml` (recommendation algorithm, scoring, explanation logic), `/domain-api` (route handler, service layer, response model), `/domain-frontend` (dropdown population, card rendering)
- **Related Use Case Skills:** `/uc-02-run-backtest-validation` (validates recommendation accuracy in aggregate), `/uc-05-view-system-statistics` (provides context on data shape before selecting a team)
