---
name: uc-02-run-backtest-validation
description: Rolling window validation of the global two-month adaptive blend, split into primary and sensitivity results. Use when modifying the backtest tab, per-month results display, or cancellation behavior. No user-adjustable model parameters exist.
---

# UC-02: Run Backtest Validation

## Summary
User runs a rolling window backtest to measure how accurately the global two-month adaptive blend predicts real team improvements across all prediction months. There are no user-adjustable model parameters - each prediction month replays the same month-specific policy the live recommendation flow would have selected at that point in time (see `/domain-ml`).

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with ≥ 4 months of data loaded; user is on the Backtest tab

## Trigger
User navigates to the Backtest tab and clicks "Run Backtest Validation".

## Main Flow
1. User navigates to Backtest tab - no configuration form is shown; there is nothing to adjust
2. Clicks "Run Backtest Validation" → `POST /api/backtest` (no request body)
3. Loading spinner displayed; button disabled during run; a "Cancel Backtest" button appears
4. For each prediction month, `BacktestEngine` builds the fixed evaluable cohort, selects that month's blend policy and its independently-selected time-aware-popularity comparison arm (same walk-forward rule, restricted to pure popularity), and scores both on the same cases
5. Results appear as two labelled sections plus a combined per-month table:
   - **Primary Results** (months with a complete 3-snapshot outcome window): blend accuracy vs random baseline, blend vs time-aware popularity (with the percentage-point difference), supplementary rank-aware metrics (Precision@N, Recall@N, MRR)
   - **Sensitivity Results** (all prediction months, including truncated outcome windows): the same figures, kept strictly separate from primary - never averaged together
   - **Per-month table:** month, scope (Primary/Sensitivity), evaluable cases, correct, blend accuracy, time-aware popularity accuracy, the difference, precision/recall/MRR, and the selected policy for that month (or "Bootstrap" if no prior month had a completed outcome window yet)
6. User can compare accuracy across months to detect stability, and can cancel a long run via "Cancel Backtest"

## Alternative / Error Flows
- **Less than 4 months of data:** API returns 400 with "Need at least 4 time periods" — error shown inline
- **A scope has zero qualifying months** (e.g. a cancelled run that stopped before any primary month completed): that section shows "Not enough completed months to report this scope" rather than a misleading 0%
- **Team has no improvements in a month's outcome window:** that team-month case is excluded from the evaluable cohort for every policy and both reported arms alike (not a partial exclusion that could differ between the blend and the popularity arm)
- **Cancellation mid-run:** the in-progress month is dropped entirely (not partially scored); `cancelled: true` is returned along with whatever complete months preceded it
- **Request timeout (long runs):** server uses a keep-alive timeout; if it expires, frontend shows a network error

## Cross-references
- **Related Domain Skills:** `/domain-validation` (`BacktestEngine` algorithm, primary/sensitivity split, random and time-aware-popularity baseline formulas), `/domain-ml` (`PolicyEngine` owns the cohort, monthly selection, and scoring the backtest replays), `/domain-api` (route + cancel handler), `/domain-frontend` (backtest tab rendering)
- **Related Use Case Skills:** `/uc-01-get-recommendations` (the same `PolicyEngine` selection this backtest replays month-by-month)
