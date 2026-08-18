---
name: uc-01-get-recommendations
description: Team + month selection → exactly two practice recommendations from that month's globally selected policy, with scores, explanations, policy audit, and validation. Use when modifying the recommendations tab, request/response flow, or how results are rendered.
---

# UC-01: Get Recommendations

## Summary
User selects a team and a prediction month; the system returns exactly two recommended practices to improve, using that month's globally selected blend policy (similarity / sequence / time-aware popularity), each with a confidence score, current maturity level, explanation, and validation against actual historical improvements. There is no per-request tuning - peer count, factor weights, and popularity recency are all chosen by the monthly policy, not by the caller. The CLI's "Get Recommendations" option produces identical output (same two practices, same order, same policy) for the same team and month, since both call the same `PolicyEngine`.

## Actor & Preconditions
- **Actor:** Analyst (web UI or CLI)
- **Preconditions:** Server running with data loaded; target team has a usable baseline snapshot before the selected month; selected month is a valid prediction month (`PolicyEngine.prediction_months()`, global index 3+)

## Trigger
User opens the Recommendations tab (default on page load), selects a team from the dropdown, selects a prediction month, and clicks "Get Recommendations". (Or, in the CLI, selects menu option 1.)

## Main Flow
1. Page loads → `GET /api/teams` populates the team dropdown (teams sorted by number of months, most history first)
2. User selects a team → `GET /api/teams/{team_name}/months` populates the month dropdown with valid prediction months (team must have a usable baseline before that month)
3. "Get Recommendations" button enables once both selections are made
4. User clicks button → `POST /api/recommendations` with `{ team, month, top_n: 2 }` (`top_n` must be exactly 2 - any other value is rejected by Pydantic validation, not silently substituted)
5. Server: `APIService.get_recommendations()` → `RecommendationEngine.recommend()` → `PolicyEngine.recommend()` selects that month's policy and scores the team's candidate practices
6. Response returns a recommendations list (practice name, score, current level, explanation, similar_teams list, validated flag), plus `selected_policy` (the audit record: peer count, similarity threshold, factor weights, popularity recency, bootstrap flag) and `no_similar_teams_found`
7. UI renders each recommendation as a card (practice name, score, current maturity level, "why" text), a policy audit box showing the selected policy, and the validation section
8. Practice profile panel shows all practices grouped into Level 0–3 maturity buckets
9. Validation panel shows what actually improved in the predicted month and up to 2 observed snapshots ahead, with hit/miss indicators on each recommendation card

## Alternative / Error Flows
- **Team has no valid prediction months:** month dropdown stays empty; button stays disabled
- **Team has fewer than two non-maxed candidate practices:** no recommendations are returned; the response's `message` field explains why (e.g. "Team 'X' has fewer than two practices left to improve.") - this is not an error, it's a valid outcome shown in place of recommendation cards
- **No comparable peer team found:** similarity contributes zero for every candidate; two recommendations are still returned from sequence + popularity evidence; `no_similar_teams_found` is `true` and the "why" text for affected practices says so explicitly, rather than silently showing an empty peer list
- **No improvements in validation window:** validation panel shows "No improvements recorded" — this is not a model failure
- **Accuracy = None:** shown as "—" rather than a percentage when no improvements occurred in the window
- **The first several prediction months use the bootstrap policy** (100% popularity, 50/50 recency) because no prior prediction month yet has a completed 3-snapshot outcome window - the audit box shows peer count and similarity threshold as "N/A", never a default value

## Cross-references
- **Related Domain Skills:** `/domain-ml` (`PolicyEngine`: policy selection, scoring, explanation logic), `/domain-api` (route handler, service layer, response model), `/domain-frontend` (dropdown population, card + policy-audit-box rendering)
- **Related Use Case Skills:** `/uc-02-run-backtest-validation` (validates the same `PolicyEngine` in aggregate, replaying the same month-specific policy selection), `/uc-05-view-system-statistics` (provides context on data shape before selecting a team)
