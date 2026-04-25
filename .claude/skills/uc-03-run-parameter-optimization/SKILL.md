---
name: uc-03-run-parameter-optimization
description: Grid search over parameter combinations to find highest-accuracy config. Use when modifying optimization param ranges, the cancel flow, or how results are displayed/saved.
---

# UC-03: Run Parameter Optimization

## Summary
User configures parameter ranges and launches a grid search that runs a full backtest for every combination, returning the configuration with the highest accuracy.

## Actor & Preconditions
- **Actor:** Analyst
- **Preconditions:** Server running with ≥ 4 months of data; user is on the Backtest tab (optimization section)

## Trigger
User configures parameter ranges (or accepts defaults), sets a minimum accuracy target, and clicks "Find Optimal Config".

## Main Flow
1. User expands the optimization section on the Backtest tab
2. Optionally sets ranges for: top_n, similarity_weight, k_similar, lookahead months, recent months, min similarity threshold
3. Sets minimum accuracy threshold (default 40%)
4. Clicks "Find Optimal Config" → `POST /api/optimize`
5. Cancel button appears; run executes in background (server-side thread pool)
6. On completion, results display:
   - Best configuration found (all parameter values)
   - Accuracy achieved and improvement factor over random baseline
   - Total combinations tested vs available
   - Ranked table of all tested combinations
7. Latest results are also saved to `results/` directory and retrievable via `GET /api/optimize/latest`

## Alternative / Error Flows
- **User clicks Cancel during run:** `POST /api/optimize/cancel` sets cancellation flag → partial results returned with "Cancelled" notice; tested combinations and best-so-far config shown
- **No config found above min_accuracy threshold:** if not cancelled, API returns 400; if cancelled, partial results still shown
- **Very large parameter space:** each combination runs a full backtest (seconds each); 180+ combinations can take several minutes

## Cross-references
- **Related Domain Skills:** `/domain-validation` (OptimizationEngine, grid search, cancellation flag), `/domain-api` (optimize route, ThreadPoolExecutor pattern), `/domain-frontend` (optimization form, cancel button)
- **Related Use Case Skills:** `/uc-02-run-backtest-validation` (single run with a specific config), `/uc-01-get-recommendations` (uses the optimized params)
