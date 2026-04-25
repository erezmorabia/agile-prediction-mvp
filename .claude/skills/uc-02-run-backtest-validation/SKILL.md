---
name: uc-02-run-backtest-validation
description: Rolling window accuracy validation against historical data. Use when modifying the backtest tab, parameter config form, per-month results display, or cancellation behavior.
---

# UC-02: Run Backtest Validation

## Summary
User runs a rolling window backtest to measure how accurately the current parameter configuration predicts real team improvements across all historical months.

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with ≥ 4 months of data loaded; user is on the Backtest tab

## Trigger
User navigates to the Backtest tab and clicks "Run Backtest Validation".

## Main Flow
1. User navigates to Backtest tab
2. Optionally adjusts configuration parameters (top_n, k_similar, similarity_weight, lookahead months, etc.) via form inputs shown on the tab
3. Clicks "Run Backtest" → `POST /api/backtest` with optional config dict
4. Loading spinner displayed; button disabled during run
5. Results appear showing:
   - Overall accuracy % and random baseline %
   - Improvement factor (e.g., "2.0× better than random")
   - Total predictions and correct predictions
   - Per-month breakdown table (month, predictions, correct, accuracy)
6. User can compare accuracy across months to detect stability

## Alternative / Error Flows
- **Less than 4 months of data:** API returns 400 with "Need at least 4 time periods" — error shown inline
- **No improvements in a month's teams:** those teams are silently excluded from that month's accuracy calculation; month still appears in results with lower team count
- **Request timeout (long runs):** server uses 5-minute keep-alive timeout; if it expires, frontend shows network error

## Cross-references
- **Related Domain Skills:** `/domain-validation` (BacktestEngine algorithm, rolling window logic, random baseline formula), `/domain-api` (route handler, config model), `/domain-frontend` (backtest tab rendering)
- **Related Use Case Skills:** `/uc-01-get-recommendations` (same ML params used for individual predictions), `/uc-03-run-parameter-optimization` (automates running many backtests to find best params)
